"""Every ``sq migrate up`` run that ends with the schema stamp unchanged names, as something to
run, only commands the gate lets past a squad that is behind. The permitted set is read from the
grants the commands declare; a run that escapes a runner or the trailing repair says the squad is
still behind and that re-running ``sq migrate up`` is the way forward; the ordinary callers of
the shared messages keep their wording at the current schema.
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

from _helpers import make_service
from squads import __version__
from squads._cli._migrate import migrate_grants
from squads._errors import IndexFullError, SquadsError
from squads._migrations import _registry
from squads._migrations._registry import MigrationOutcome
from squads._models._index import SquadsDB
from squads._models._schema import SCHEMA_VERSION
from squads._services import _maintenance
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_TASK = "tasks/TASK-000003-implement-auth.md"
_MILE = "milestones/MILE-000011-ship-the-auth-module.md"
_ITEM = (
    "---\nid: {id}\nsequence_id: {seq}\ntype: {type}\ntitle: T\nslug: s\nstatus: {status}\n"
    "created_at: '2025-01-01T00:00:00Z'\nupdated_at: '2025-01-01T00:00:00Z'\n---\nbody\n"
)
_WORD = r"(<[^>\s]+>|[a-z][\w-]*)"
_COMMAND = re.compile(rf"\bsq {_WORD}(?: {_WORD})?")


def _permitted() -> set[str]:
    return {f"migrate {name}" for name, grant in migrate_grants().items() if grant.behind}


def _named_commands(text: str) -> set[str]:
    found: set[str] = set()
    for first, second in _COMMAND.findall(text):
        found.add(f"{first} {second}" if first == "migrate" and second else first)
    return found


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


def _override(root: Path, body: str) -> None:
    _put(root, ".overrides/workflow.toml", f"# squads:override-base:{__version__}\n{body}")


def _edit(root: Path, rel: str, old: str, new: str) -> None:
    text = (root / rel).read_text(encoding="utf-8")
    assert old in text, old
    (root / rel).write_text(text.replace(old, new, 1), encoding="utf-8")


@pytest.fixture
def squad(tmp_path: Path, frozen_time: object) -> Path:
    root = tmp_path / "v0_14"
    shutil.copytree(_CORPUS_DIR / "v0_14", root)
    return root


def _forget_milestone(root: Path) -> None:
    index = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    index["items"] = {k: v for k, v in index["items"].items() if v["path"] != _MILE}
    (root / ".squads.json").write_text(json.dumps(index), encoding="utf-8")


def _no_index_beside_an_archived_item(root: Path) -> None:
    _put(
        root,
        "archive/MILE-000030-old.md",
        _ITEM.format(id="MILE-30", seq=30, type="milestone", status="Draft"),
    )
    (root / ".squads.json").unlink()


def _no_index_beside_a_look_alike(root: Path) -> None:
    _put(root, "docs/ADR-20240116-x.md", b"\xff\xfe")
    (root / ".squads.json").unlink()


def _misplace_the_task(root: Path) -> None:
    (root / "attic").mkdir()
    shutil.move(root / _TASK, root / "attic/TASK-000003-implement-auth.md")
    index = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    for value in index["items"].values():
        if value["path"] == _TASK:
            value["path"] = "attic/TASK-000003-implement-auth.md"
    (root / ".squads.json").write_text(json.dumps(index), encoding="utf-8")


_REVIEW = "reviews/REV-000006-auth-module-review.md"
_MIRRORS = '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n'


def _stranded_item_badge(root: Path) -> None:
    _edit(root, _TASK, "status: InProgress", "status: InProgress\npriority: urgentest")


def _stranded_subentity_badge(root: Path) -> None:
    _edit(root, _REVIEW, "severity: high", "severity: catastrophic")


_LEVELS = (
    '[collections.level]\nlabel = "Level"\nordered = true\n'
    'badges = [{ code = "high", label = "High" }]\n'
    '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n'
    'fields = [{ code = "impact", label = "Impact", collection = "level" }]\n'
)


def _incident_with_impact(value: str) -> Callable[[Path], None]:
    def _stage(root: Path) -> None:
        _override(root, _LEVELS)
        _put(
            root,
            "incidents/INC-000020-an-incident.md",
            "---\nid: INC-20\nsequence_id: 20\ntype: incident\ntitle: An incident\n"
            f"slug: an-incident\nstatus: Draft\nextra:\n  impact: {value}\n"
            "created_at: '2025-01-01T00:00:00Z'\nupdated_at: '2025-01-01T00:00:00Z'\n---\nbody\n",
        )
        (root / ".squads.json").unlink()

    return _stage


_REFUSALS: dict[str, Callable[[Path], None]] = {
    "custom-badge-is-a-list": _incident_with_impact("[high, low]"),
    "custom-badge-is-a-mapping": _incident_with_impact("{a: 1}"),
    "custom-badge-is-a-number": _incident_with_impact("3"),
    "custom-badge-is-undeclared": _incident_with_impact("nope"),
    "hand-edited-item-badge": _stranded_item_badge,
    "hand-edited-subentity-badge": _stranded_subentity_badge,
    "hand-edited-item-badge-beside-an-override": lambda r: (
        _override(r, _MIRRORS),
        _stranded_item_badge(r),
    )[0],
    "hand-edited-subentity-badge-beside-an-override": lambda r: (
        _override(r, _MIRRORS),
        _stranded_subentity_badge(r),
    )[0],
    "undecodable-bytes": lambda r: _put(r, _TASK, (r / _TASK).read_bytes() + b"\xff"),
    "frontmatter-does-not-parse": lambda r: _edit(r, _TASK, "---\n", "---\nbroken: [x\n"),
    "no-frontmatter": lambda r: _put(r, _TASK, "# prose\n"),
    "one-id-in-two-files": lambda r: _put(r, "tasks/notes.md", (r / _TASK).read_bytes()),
    "two-ids-one-number": lambda r: _put(
        r, "bugs/BUG-000003-x.md", _ITEM.format(id="BUG-3", seq=3, type="bug", status="Open")
    ),
    "no-index-beside-an-archived-item": lambda r: _no_index_beside_an_archived_item(r),
    "no-index-beside-an-unreadable-look-alike": lambda r: _no_index_beside_a_look_alike(r),
    "first-item-of-a-type-unindexed": _forget_milestone,
    "indexed-file-where-no-type-lives": _misplace_the_task,
    "override-drops-a-type": lambda r: _override(
        r, "[selected]\nitems = ['task', 'bug', 'feature', 'epic']\n"
    ),
    "override-re-prefixes-a-type": lambda r: _override(r, '[items.task]\nprefix = "WORK"\n'),
    "hand-edited-status": lambda r: _edit(r, _TASK, "status: InProgress", "status: Triaged"),
    "hand-edited-type": lambda r: _edit(r, _TASK, "type: task", "type: zzz"),
    "hand-edited-subentity-status": lambda r: _edit(r, _TASK, "status: Todo", "status: Bogus"),
    "badge-collection-shrunk": lambda r: (
        _edit(r, _TASK, "status: InProgress", "status: InProgress\npriority: high"),
        _override(
            r,
            '[collections.priority]\nlabel = "Priority"\nordered = true\n'
            'badges = [{ code = "urgent", label = "Urgent" }]\n',
        ),
    )[0],
    "workflow-override-not-toml": lambda r: _put(r, ".overrides/workflow.toml", "[items.x\n==="),
    "workflow-override-fails-validation": lambda r: _override(
        r, '[items.task]\nlifecycle = "no-such-lifecycle"\n'
    ),
    "workflow-override-two-default-ref-kinds": lambda r: _override(
        r, '[ref_kinds.blocks]\nrole = "default"\n'
    ),
    "playbook-override-fails": lambda r: _put(
        r, ".overrides/playbook.toml", f"# squads:override-base:{__version__}\n[types.nope\n"
    ),
}


@pytest.mark.parametrize("row", _REFUSALS)
async def test_a_refused_run_names_only_commands_the_gate_permits_behind(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    _REFUSALS[row](squad)
    before = _md(squad)
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert _stamp(squad) == "0.14"
    refusal = result.output
    if row.startswith("custom-badge"):
        assert "INC-000020-an-incident.md" in refusal and "'impact'" in refusal
    assert _named_commands(refusal) <= _permitted(), refusal
    assert "migrate up" in " ".join(refusal.split())
    assert _md(squad) == before


# --------------------------------------------------------------------------- a runner that raises


def _raising_runner(monkeypatch: pytest.MonkeyPatch, *, after_running_it: bool) -> None:
    def _wrap(m: Any) -> Any:
        async def _run(ctx: Any) -> Any:
            if not after_running_it:
                raise SquadsError("injected failure")
            await m.run(ctx)
            raise SquadsError("injected failure")

        return dataclasses.replace(m, run=_run)

    wrapped = [_wrap(m) if m.to_schema == "0.15" else m for m in _registry.MIGRATIONS]
    monkeypatch.setattr(_maintenance, "MIGRATIONS", wrapped)


@pytest.mark.parametrize("after_running_it", [False, True], ids=["before-a-write", "after-a-write"])
async def test_a_runner_that_raises_leaves_the_squad_behind_and_a_second_run_completes(
    after_running_it: bool, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    monkeypatch.chdir(squad)
    with monkeypatch.context() as patch:
        _raising_runner(patch, after_running_it=after_running_it)
        first = await invoke(["migrate", "up"])
    written = (squad / _MILE).read_bytes()

    assert first.exit_code == 1, first.output
    out = " ".join(first.output.split())
    assert "injected failure" in out
    assert "The squad is still at schema v0.14: fix the cause, then re-run `sq migrate up`" in out
    assert _named_commands(first.output) <= _permitted()
    assert _stamp(squad) == "0.14"
    assert ("sq:view:milestone_rollup" in written.decode()) == after_running_it

    second = await invoke(["migrate", "up"])

    assert second.exit_code == 0, second.output
    assert _stamp(squad) == SCHEMA_VERSION
    if after_running_it:
        assert (squad / _MILE).read_bytes() == written


# --------------------------------------------------------------------------- the trailing repair


_HAND_EDITS = {
    "status": ("status: InProgress", "status: Triaged"),
    "type": ("type: task", "type: zzz"),
    "subentity-status": ("status: Todo", "status: Bogus"),
}


@pytest.mark.parametrize("row", _HAND_EDITS)
async def test_the_trailing_repairs_vocabulary_refusal_names_the_command_the_gate_permits(
    row: str, squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    async def _nothing(ctx: Any) -> MigrationOutcome:
        return MigrationOutcome(count=0)

    monkeypatch.setattr(_maintenance.MaintenanceMixin, "_pre_runner_refusal", lambda *a, **k: None)
    inert = [
        dataclasses.replace(m, run=_nothing) if m.to_schema in ("0.15", "0.16") else m
        for m in _registry.MIGRATIONS
    ]
    monkeypatch.setattr(_maintenance, "MIGRATIONS", inert)
    _edit(squad, _TASK, *_HAND_EDITS[row])
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    out = " ".join(result.output.split())
    assert result.exit_code == 1, result.output
    assert "before running `sq migrate up`" in out or "re-run `sq migrate up`" in out
    assert _named_commands(result.output) <= _permitted()
    assert _stamp(squad) == "0.14"


async def test_the_trailing_repairs_alignment_refusal_names_no_refused_command(
    squad: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    monkeypatch.setattr(_maintenance, "corpus_fit_refusal", lambda *a, **k: None)
    _override(squad, '[items.task]\nprefix = "WORK"\n')
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert _named_commands(result.output) <= _permitted()
    assert _stamp(squad) == "0.14"


# --------------------------------------------------------------------------- a full index


async def test_a_full_index_with_an_id_hungry_runner_pending_is_refused_without_repad(
    tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    monkeypatch.chdir(tmp_path)
    built = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    toml = (tmp_path / ".squads.toml").read_text(encoding="utf-8")
    (tmp_path / ".squads.toml").write_text(
        toml.replace(f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.8"'),
        encoding="utf-8",
    )
    index = json.loads(built.paths.index_path.read_text(encoding="utf-8"))
    index["counter"], index["padding"] = 999_999, 6
    built.paths.index_path.write_text(json.dumps(index), encoding="utf-8")

    result = await invoke(["migrate", "up"])

    out = " ".join(result.output.split())
    assert result.exit_code == 1, result.output
    assert "the index is full" in out and "999,999" in out
    assert "repad" not in out
    assert "reads schema v0.8" in out
    assert _named_commands(result.output) <= _permitted()
    assert (tmp_path / ".squads.toml").read_text(encoding="utf-8").count('schema_version = "0.8"')


# --------------------------------------------------------------------------- ordinary callers


def test_allocate_id_keeps_its_own_wording_and_raises_the_specific_error() -> None:
    db = SquadsDB(counter=9, padding=1)

    with pytest.raises(IndexFullError) as excinfo:
        db.allocate_id("task", prefix="TASK")

    assert str(excinfo.value) == (
        "index is full: all 9 IDs at padding 1 are used up. "
        "Raise the padding with `sq migrate repad <new-width>`."
    )
    assert isinstance(excinfo.value, SquadsError)


async def test_repair_at_the_current_schema_still_says_sq_repair(
    tmp_path: Path, frozen_time: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    built = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = make_service(built.paths)
    task = (await svc.create("task", "t", author="manager")).item
    path = built.paths.abspath(task.path)
    path.write_text(
        path.read_text(encoding="utf-8").replace("status: Draft", "status: Triaged"),
        encoding="utf-8",
    )

    with pytest.raises(SquadsError, match="before running `sq repair`"):
        await svc.repair()
    with pytest.raises(SquadsError, match="before running `sq migrate up`"):
        await svc.repair(rerun="`sq migrate up`")


async def test_a_header_name_that_resolves_to_no_entry_names_only_permitted_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke: Any
) -> None:
    root = tmp_path / "v0_15_discussions"
    shutil.copytree(_CORPUS_DIR / "v0_15_discussions", root)
    (role,) = root.glob("agents/roles/*-python-dev.md")
    _edit(root, role.relative_to(root).as_posix(), "title: Elias Python", "title: Elias Renamed")
    monkeypatch.chdir(root)

    result = await invoke(["migrate", "up"])

    out = " ".join(result.output.split())
    assert result.exit_code == 1, result.output
    assert "matches no roster entry" in out and _stamp(root) == "0.15"
    assert _named_commands(result.output) <= _permitted()
    assert "re-run `sq migrate up`" in out
