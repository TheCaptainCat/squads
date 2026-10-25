"""A squad whose schema differs from the package's either migrates through ``sq migrate up`` to
the same corpus a clean squad reaches, or is refused before any item file changes with a cause it
can act on; the position is asserted after every command, never only an exit code.

One table of mutations over a squad stamped 0.14 whose two milestones carry no roll-up tag yet,
plus aged squads for the rows that need an older stamp, all driven through the Typer app.
"""

import dataclasses
import hashlib
import json
import re
import shutil
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import anyio
import pytest

from _helpers import make_service, make_unreadable_by_the_os
from squads import __version__
from squads._cli._migrate import migrate_grants
from squads._errors import SquadsError
from squads._migrations import _registry
from squads._models import _markers as markers
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._services import _maintenance
from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

type Mutation = Callable[[Path], None]

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
#: The installed `sq` console script, so one row exercises the real entry point.
_SQ_BIN = Path(sys.executable).parent / "sq"
_TAG = markers.open_marker(markers.view_tag("milestone_rollup"))
_MILE_1 = "squads/milestones/MILE-000002-first.md"
_MILE_2 = "squads/milestones/MILE-000003-second.md"
_TASK = "squads/tasks/TASK-000004-a-task.md"
_RENAMED = "squads/tasks/TASK-000004-renamed-task.md"
_WORD = r"(<[^>\s]+>|[a-z][\w-]*)"
_COMMAND = re.compile(rf"\bsq {_WORD}(?: {_WORD})?")


# --------------------------------------------------------------------------- instruments


def _permitted() -> set[str]:
    return {f"migrate {name}" for name, grant in migrate_grants().items() if grant.behind}


def _named_commands(text: str) -> set[str]:
    found: set[str] = set()
    for first, second in _COMMAND.findall(text):
        found.add(f"{first} {second}" if first == "migrate" and second else first)
    return found


def _stamp(root: Path) -> str:
    return tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]


def _set_stamp(root: Path, version: str) -> None:
    cfg = root / ".squads.toml"
    cfg.write_text(
        re.sub(r'schema_version = "[^"]+"', f'schema_version = "{version}"', cfg.read_text()),
        encoding="utf-8",
    )


def _md(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.md"))
        if p.is_file()
    }


def _own_md(root: Path) -> dict[str, str]:
    """The item files that are not generated skills, whose sequence numbers and file names
    follow the history of the run that wrote them."""
    return {
        k: v
        for k, v in _md(root).items()
        if "agents/skills/" not in k and ".claude/skills/" not in k
    }


def _everything(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


def _index_file(root: Path) -> Path:
    cfg = tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))
    return root / cfg["squad_dir"] / ".squads.json"


def _overrides_dir(root: Path, name: str) -> str:
    return (_index_file(root).parent.relative_to(root) / ".overrides" / f"{name}.toml").as_posix()


def _index(root: Path) -> dict[str, Any]:
    return json.loads(_index_file(root).read_text(encoding="utf-8"))


def _indexed_paths(root: Path) -> set[str]:
    squad_dir = _index_file(root).parent.relative_to(root)
    return {(squad_dir / v["path"]).as_posix() for v in _index(root)["items"].values()}


def _write_index(root: Path, edit: Callable[[dict[str, Any]], None]) -> None:
    data = _index(root)
    edit(data)
    _index_file(root).write_text(json.dumps(data), encoding="utf-8")


def _entry(data: dict[str, Any], path: str) -> dict[str, Any]:
    return next(v for v in data["items"].values() if v["path"].endswith(path.split("/", 1)[-1]))


def _put(root: Path, rel: str, content: str | bytes) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        (root / rel).write_bytes(content)
    else:
        (root / rel).write_text(content, encoding="utf-8", newline="")


def _edit(root: Path, rel: str, old: str, new: str) -> None:
    text = (root / rel).read_text(encoding="utf-8")
    assert old in text, old
    (root / rel).write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def _override(root: Path, body: str, name: str = "workflow") -> None:
    _put(root, _overrides_dir(root, name), f"# squads:override-base:{__version__}\n{body}")


def _error_text(output: str) -> str:
    return " ".join(output.replace("\\", "/").split())


def _body_region(text: str) -> str:
    return text[text.index("<!-- sq:body -->") : text.index("<!-- sq:body:end -->")]


async def _build(root: Path) -> Path:
    """A squad of two milestones and a task, made to look as it did before the roll-up tag
    moved onto the milestones, and stamped 0.14."""
    await anyio.Path(root).mkdir(parents=True)
    built = await service.init(root=root, roles_spec="minimal", _skip_skill_seed=True)
    svc = make_service(built.paths)
    await svc.create("milestone", "First", author="manager")
    await svc.create("milestone", "Second", author="manager")
    await svc.create("task", "A task", author="manager")
    for rel in (_MILE_1, _MILE_2):
        _edit(root, rel, _TAG + "\n", "")
    _set_stamp(root, "0.14")
    return root


@pytest.fixture
async def squad(tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = await _build(tmp_path / "squad")
    monkeypatch.chdir(root)
    return root


class _FirstRunnerProbe:
    """Records the item files' digests at the point just before the first runner starts."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.seen: dict[str, str] | None = None

    def install(self, patch: pytest.MonkeyPatch) -> None:
        original = _maintenance.MaintenanceMixin._pre_runner_refusal

        def _watch(svc: Any, *args: Any, **kwargs: Any) -> Any:
            self.seen = _md(self.root)
            return original(svc, *args, **kwargs)

        patch.setattr(_maintenance.MaintenanceMixin, "_pre_runner_refusal", _watch)


# --------------------------------------------------------------------------- squads that complete


def _tag_by_hand(root: Path) -> None:
    text = (root / _MILE_1).read_text(encoding="utf-8")
    text = text.replace("<!-- sq:body:end -->", _TAG + "\n<!-- sq:body:end -->", 1)
    text = re.sub(r"updated_at: '[^']+'", "updated_at: '2026-07-01T00:00:00Z'", text, count=1)
    (root / _MILE_1).write_text(text, encoding="utf-8", newline="")


def _move_the_task(root: Path) -> None:
    shutil.move(root / _TASK, root / _RENAMED)


@dataclasses.dataclass(frozen=True)
class Completes:
    mutate: Mutation
    #: Files whose final content is the row's own, or that the row removes or adds.
    differs: frozenset[str] = frozenset()
    reconcile_line: bool = False
    tagged: tuple[str, ...] = (_MILE_1, _MILE_2)
    reflog: str = ""
    #: Item files the row leaves indexed that the clean squad does not have.
    now_indexed: frozenset[str] = frozenset()


_COMPLETES: dict[str, Completes] = {
    "clean": Completes(lambda r: None),
    "index-missing": Completes(lambda r: _index_file(r).unlink(), reconcile_line=True),
    "index-not-json": Completes(
        lambda r: _put(_index_file(r).parent, ".squads.json", "{ not json"),
        reconcile_line=True,
    ),
    "index-invalid-for-the-model": Completes(
        lambda r: _put(_index_file(r).parent, ".squads.json", '{"counter": "x"}'),
        reconcile_line=True,
    ),
    "stale-entry-with-an-undeclared-status": Completes(
        lambda r: _write_index(r, lambda d: _entry(d, _TASK).update(status="Triaged"))
    ),
    "file-the-index-lacks": Completes(
        lambda r: _write_index(
            r,
            lambda d: d["items"].pop(
                next(k for k, v in d["items"].items() if v["path"].endswith("second.md"))
            ),
        ),
        reconcile_line=True,
    ),
    "entry-whose-file-is-gone": Completes(
        lambda r: (r / _MILE_2).unlink(),
        differs=frozenset({_MILE_2}),
        reconcile_line=True,
        tagged=(_MILE_1,),
        reflog="MILE-3",
    ),
    "rename-interrupted": Completes(
        _move_the_task,
        differs=frozenset({_TASK, _RENAMED}),
        now_indexed=frozenset({_RENAMED}),
    ),
    "override-consistent": Completes(
        lambda r: _override(r, '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n')
    ),
    "override-with-a-stale-index-entry": Completes(
        lambda r: (
            _override(r, '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n'),
            _write_index(r, lambda d: _entry(d, _TASK).update(status="Triaged")),
        )[0]
    ),
    "value-ahead-of-the-index": Completes(
        lambda r: _edit(r, _TASK, "title: A task", "title: A hand-edited task"),
        differs=frozenset({_TASK}),
    ),
    "partial-pass": Completes(_tag_by_hand, differs=frozenset({_MILE_1})),
}


@pytest.mark.parametrize("row", _COMPLETES)
async def test_a_squad_that_can_migrate_ends_where_the_clean_squad_ends(
    row: str, tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    spec = _COMPLETES[row]
    reference = await _build(tmp_path / "reference")
    monkeypatch.chdir(reference)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    reference_md = _md(reference)
    reference_paths = _indexed_paths(reference)

    root = await _build(tmp_path / "row")
    spec.mutate(root)
    probe = _FirstRunnerProbe(root)
    before = _md(root)
    monkeypatch.chdir(root)
    with monkeypatch.context() as patch:
        probe.install(patch)
        result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(root) == SCHEMA_VERSION
    assert probe.seen == before, "an item file changed before the first runner"
    assert ("index reconciled with the files" in result.output) == spec.reconcile_line
    for rel in spec.tagged:
        text = (root / rel).read_text(encoding="utf-8")
        assert text.count(_TAG) == 1 and _TAG in _body_region(text)
    final = _md(root)
    assert {k: v for k, v in final.items() if k not in spec.differs} == {
        k: v for k, v in reference_md.items() if k not in spec.differs
    }
    assert _indexed_paths(root) == {p for p in reference_paths if (root / p).exists()} | set(
        spec.now_indexed
    )
    assert (await invoke(["check"])).exit_code == 0
    assert (await invoke(["list"])).exit_code == 0
    if spec.reflog:
        reflog = (root / "squads/.reflog.jsonl").read_text(encoding="utf-8")
        assert spec.reflog in reflog

    settled = _everything(root)
    again = await invoke(["migrate", "up"])

    assert again.exit_code == 0 and "nothing to migrate" in again.output
    assert _everything(root) == settled


# --------------------------------------------------------------------------- squads refused

#: Stages a failure and returns what an operator does by hand to remove it.
type Stage = Callable[[Path], Callable[[], None]]


def _by_restoring(root: Path, rel: str, damage: Callable[[], None]) -> Callable[[], None]:
    original = (root / rel).read_bytes()
    damage()

    def _restore() -> None:
        (root / rel).write_bytes(original)

    return _restore


def _undecodable(rel: str) -> Stage:
    return lambda r: _by_restoring(r, rel, lambda: _put(r, rel, (r / rel).read_bytes() + b"\xff"))


def _broken_frontmatter(rel: str) -> Stage:
    return lambda r: _by_restoring(r, rel, lambda: _edit(r, rel, "---\n", "---\nbroken: [x\n"))


def _identity_lost(rel: str) -> Stage:
    return lambda r: _by_restoring(r, rel, lambda: _edit(r, rel, "id: TASK-4\n", ""))


def _hand_edited_status(rel: str) -> Stage:
    return lambda r: _by_restoring(
        r, rel, lambda: _edit(r, rel, "status: Draft", "status: Triaged")
    )


def _copied(rel: str) -> Stage:
    def _stage(root: Path) -> Callable[[], None]:
        _put(root, "squads/tasks/notes.md", (root / rel).read_bytes())
        return (root / "squads/tasks/notes.md").unlink

    return _stage


def _unreadable(rel: str) -> Stage:
    return lambda r: make_unreadable_by_the_os(r / rel)


def _overridden(body: str, name: str = "workflow", raw: bool = False) -> Stage:
    def _stage(root: Path) -> Callable[[], None]:
        if raw:
            _put(root, _overrides_dir(root, name), body)
        else:
            _override(root, body, name)
        return (root / _overrides_dir(root, name)).unlink

    return _stage


@dataclasses.dataclass(frozen=True)
class Refused:
    stage: Stage
    #: Strings the refusal must carry: the files and the cause it names.
    names: tuple[str, ...]
    #: The item file whose previous index entry must survive the refusal, if any.
    kept: str = ""


_REFUSED: dict[str, Refused] = {
    "undecodable-file": Refused(_undecodable(_TASK), ("TASK-000004-a-task.md",), _TASK),
    "frontmatter-does-not-parse-in-a-task": Refused(
        _broken_frontmatter(_TASK), ("TASK-000004-a-task.md",), _TASK
    ),
    "frontmatter-does-not-parse-in-a-milestone": Refused(
        _broken_frontmatter(_MILE_1), ("MILE-000002-first.md",), _MILE_1
    ),
    "one-id-in-two-files": Refused(_copied(_TASK), ("TASK-000004-a-task.md", "notes.md")),
    "identity-lost": Refused(_identity_lost(_TASK), ("TASK-000004-a-task.md",), _TASK),
    "read-refused-by-the-os": Refused(_unreadable(_TASK), ("TASK-000004-a-task.md",), _TASK),
    "override-drops-a-type-the-corpus-uses": Refused(
        _overridden(f"[selected]\nitems = {sorted(set(bundled_spec().items) - {'task'})!r}\n"),
        (".overrides/workflow.toml", "task"),
    ),
    "workflow-override-is-not-toml": Refused(
        _overridden("[items.x\n===", raw=True), ("workflow.toml",)
    ),
    "playbook-override-does-not-load": Refused(
        _overridden("[types.nope\n", "playbook"), ("playbook.toml",)
    ),
    "hand-edited-badge-code": Refused(
        lambda r: _by_restoring(
            r, _TASK, lambda: _edit(r, _TASK, "status: Draft", "status: Draft\npriority: urgentest")
        ),
        ("urgentest",),
    ),
    "hand-edited-status": Refused(_hand_edited_status(_TASK), ("Triaged",)),
}


@pytest.mark.parametrize("row", _REFUSED)
async def test_a_squad_that_cannot_migrate_is_refused_untouched_and_the_remedy_works(
    row: str, squad: Path, invoke: Any
) -> None:
    spec = _REFUSED[row]
    fix = spec.stage(squad)
    index_before = _index(squad)["items"]
    everything_before = _everything(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert _stamp(squad) == "0.14"
    refusal = _error_text(result.output)
    for name in spec.names:
        assert name in refusal, refusal
    assert _named_commands(refusal) <= _permitted(), refusal
    assert _everything(squad).keys() == everything_before.keys()
    assert _md(squad) == {k: v for k, v in everything_before.items() if k.endswith(".md")}
    if spec.kept:
        assert [
            v for v in _index(squad)["items"].values() if v["path"].endswith(spec.kept[8:])
        ] == [v for v in index_before.values() if v["path"].endswith(spec.kept[8:])]

    fix()
    again = await invoke(["migrate", "up"])

    assert again.exit_code == 0, again.output
    assert _stamp(squad) == SCHEMA_VERSION
    assert (await invoke(["check"])).exit_code == 0


# --------------------------------------------------------------------------- a run that is stopped


def _stopping_after(to_schema: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def _wrap(m: Any) -> Any:
        async def _run(ctx: Any) -> Any:
            await m.run(ctx)
            raise SquadsError("injected failure")

        return dataclasses.replace(m, run=_run)

    wrapped = [_wrap(m) if m.to_schema == to_schema else m for m in _registry.MIGRATIONS]
    monkeypatch.setattr(_maintenance, "MIGRATIONS", wrapped)


async def test_a_run_stopped_after_a_runner_wrote_is_resumed_to_the_clean_corpus(
    tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    reference = await _build(tmp_path / "reference")
    monkeypatch.chdir(reference)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    root = await _build(tmp_path / "row")
    monkeypatch.chdir(root)
    with monkeypatch.context() as patch:
        _stopping_after("0.15", patch)
        first = await invoke(["migrate", "up"])
    written = (root / _MILE_1).read_bytes()

    assert first.exit_code == 1, first.output
    assert "The squad is still at schema v0.14: fix the cause, then re-run `sq migrate up`" in (
        " ".join(first.output.split())
    )
    assert _stamp(root) == "0.14"
    assert _TAG in written.decode()
    assert _named_commands(_error_text(first.output)) <= _permitted()

    second = await invoke(["migrate", "up"])

    assert second.exit_code == 0, second.output
    assert _stamp(root) == SCHEMA_VERSION
    assert (root / _MILE_1).read_bytes() == written
    assert _md(root) == _md(reference)


# --------------------------------------------------------------------------- ahead of the package


@pytest.mark.parametrize("with_conflicting_override", [False, True], ids=["plain", "override"])
async def test_a_squad_ahead_of_the_package_is_told_to_upgrade_and_nothing_is_written(
    with_conflicting_override: bool, squad: Path, invoke: Any
) -> None:
    if with_conflicting_override:
        _overridden(f"[selected]\nitems = {sorted(set(bundled_spec().items) - {'task'})!r}\n")(
            squad
        )
    _set_stamp(squad, "0.99")
    before = _everything(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert "upgrade the squads package" in " ".join(result.output.split()).lower()
    assert "override" not in result.output
    assert _everything(squad) == before


# --------------------------------------------------------------------------- the gate

_GATED = [
    ["repair"],
    ["check"],
    ["list"],
    ["migrate", "repad", "7"],
    ["migrate", "rename-status", "task", "Draft", "Ready"],
    ["migrate", "rename-type", "task", "guide"],
]
_OPEN = [["migrate", "help"], ["migrate", "chlog", "v0.14.0..v0.15.0"]]


@pytest.mark.parametrize("stamp", ["0.14", "0.99"], ids=["behind", "ahead"])
async def test_the_gate_refuses_every_other_command_untouched_and_lets_help_and_chlog_past(
    stamp: str, squad: Path, invoke: Any
) -> None:
    _set_stamp(squad, stamp)
    before = _everything(squad)

    for argv in _GATED:
        refused = await invoke(argv)
        assert refused.exit_code == 1, (argv, refused.output)
        said = " ".join(refused.output.split()).lower()
        assert ("sq migrate up" if stamp == "0.14" else "upgrade the squads package") in said, (
            argv,
            said,
        )
        assert _everything(squad) == before, argv
    for argv in _OPEN:
        assert (await invoke(argv)).exit_code == 0, argv
    assert _everything(squad) == before


async def test_the_real_entry_point_migrates_a_clean_squad_and_refuses_a_gated_command(
    tmp_path: Path, frozen_time: object
) -> None:
    root = await _build(tmp_path / "squad")
    refused = await anyio.run_process([str(_SQ_BIN), "repair"], cwd=root, check=False)
    migrated = await anyio.run_process([str(_SQ_BIN), "migrate", "up"], cwd=root, check=False)

    assert refused.returncode == 1, refused.stderr
    assert "sq migrate up" in " ".join((refused.stderr + refused.stdout).decode().split())
    assert migrated.returncode == 0, migrated.stderr
    assert _stamp(root) == SCHEMA_VERSION


# --------------------------------------------------------------------------- aged squads


def _aged(tmp_path: Path, fixture: str, name: str) -> Path:
    root = tmp_path / name
    shutil.copytree(_CORPUS_DIR / fixture, root)
    return root


_MIRRORS = '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n'
_INCIDENT = '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n'
_INCIDENT_FILE = (
    "---\nid: INC-9\nsequence_id: 9\ntype: incident\ntitle: An incident\nslug: an-incident\n"
    "status: Draft\ncreated_at: '2025-05-20T11:00:00Z'\nupdated_at: '2025-05-20T11:00:00Z'\n---\n"
    "<!-- sq:body -->\n# An incident\n<!-- sq:body:end -->\n"
)
_INCIDENT_PATH = "incidents/INC-000009-an-incident.md"


def _add_an_incident(root: Path) -> None:
    _override(root, _INCIDENT, "workflow")
    _put(root, _INCIDENT_PATH, _INCIDENT_FILE)

    def _edit(data: dict[str, Any]) -> None:
        entry = dict(next(iter(data["items"].values())))
        entry.update(
            sequence_id=9,
            type="incident",
            title="An incident",
            slug="an-incident",
            status="Draft",
            path=_INCIDENT_PATH,
            subentities=[],
            refs=[],
            parent=None,
            attributes={},
            id="INC-9",
        )
        data["items"]["9"] = entry
        data["counter"] = 9

    _write_index(root, _edit)


#: Each older stamp, with the legacy file that makes the runner of that step open the index.
_OWN_TYPE_SQUADS = [
    pytest.param("v0_4", "agents/skills/squads.md", id="0.4-with-an-unstamped-skill"),
    pytest.param("v0_8", "agents/skills/sq-memory.md", id="0.8-with-an-unstamped-memory-skill"),
    pytest.param("v0_11", "", id="0.11"),
]


@pytest.mark.parametrize(("fixture", "legacy"), _OWN_TYPE_SQUADS)
async def test_a_squad_with_a_type_of_its_own_migrates_from_an_older_schema_keeping_the_item(
    fixture: str,
    legacy: str,
    tmp_path: Path,
    frozen_time: object,
    monkeypatch: pytest.MonkeyPatch,
    invoke: Any,
) -> None:
    reference = _aged(tmp_path, fixture, "reference")
    monkeypatch.chdir(reference)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    root = _aged(tmp_path, fixture, "row")
    _add_an_incident(root)
    if legacy:
        _put(root, legacy, "# Memory\n\nHow to keep notes.\n")
    monkeypatch.chdir(root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert _stamp(root) == SCHEMA_VERSION
    kept = [v for v in _index(root)["items"].values() if v["type"] == "incident"]
    assert [v["path"] for v in kept] == [_INCIDENT_PATH]
    assert "type: incident" in (root / _INCIDENT_PATH).read_text(encoding="utf-8")
    assert {k: v for k, v in _own_md(root).items() if k != _INCIDENT_PATH} == _own_md(reference)
    assert (await invoke(["check"])).exit_code == 0


async def test_a_squad_at_the_project_root_ignores_the_markdown_that_is_not_its_own(
    tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    reference = _aged(tmp_path, "v0_14", "reference")
    monkeypatch.chdir(reference)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    root = _aged(tmp_path, "v0_14", "row")
    strays = {
        "README.md": "# A project\n",
        "notes/plan.md": "---\nid: PLAN-1\ntitle: Plan\n---\nbody\n",
        "notes/numbered.md": "---\nid: 12\n---\nbody\n",
    }
    for rel, text in strays.items():
        _put(root, rel, text)
    monkeypatch.chdir(root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert not any(Path(rel).name in result.output for rel in strays)
    final = _md(root)
    assert {k: v for k, v in final.items() if k not in strays} == _md(reference)
    assert {k: final[k] for k in strays} == {
        k: hashlib.sha256(v.encode()).hexdigest() for k, v in strays.items()
    }


_STOP_POINTS = [m.to_schema for m in _registry.MIGRATIONS if schema_tuple(m.to_schema) > (0, 5)]


@pytest.mark.parametrize("override", ["", _MIRRORS], ids=["no-override", "override"])
@pytest.mark.parametrize("stopped_after", _STOP_POINTS)
async def test_a_pre_0_7_squad_stopped_after_any_runner_is_resumed_to_the_uninterrupted_corpus(
    stopped_after: str,
    override: str,
    tmp_path: Path,
    frozen_time: object,
    monkeypatch: pytest.MonkeyPatch,
    invoke: Any,
) -> None:
    reference = _aged(tmp_path, "v0_5", "reference")
    root = _aged(tmp_path, "v0_5", "row")
    if override:
        _override(reference, override)
        _override(root, override)
    monkeypatch.chdir(reference)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    monkeypatch.chdir(root)
    with monkeypatch.context() as patch:
        _stopping_after(stopped_after, patch)
        first = await invoke(["migrate", "up"])

    assert first.exit_code == 1, first.output
    assert _stamp(root) == "0.5"
    assert _named_commands(_error_text(first.output)) <= _permitted()

    second = await invoke(["migrate", "up"])

    assert second.exit_code == 0, second.output
    assert _stamp(root) == SCHEMA_VERSION
    assert not any(v.get("id", "").startswith("UNRESOLVED") for v in _index(root)["items"].values())
    assert _own_md(root) == _own_md(reference)
    assert (await invoke(["check"])).exit_code == 0
