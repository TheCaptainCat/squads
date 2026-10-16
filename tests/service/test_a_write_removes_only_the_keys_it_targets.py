"""Whatever write path touches an item, a frontmatter key the command did not target keeps its
name and its value: in the file, in the item's ``--json`` row and in the rebuilt index.

One table. Rows are the write paths; columns are the shapes a key can take. Each cell plants the
key on an item, runs the path, and reads the key back three ways. A witness per row shows the path
really changed what it names, so no row passes on a path that never ran; two controls show that a
command that does target a key changes it.
"""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic_core import to_jsonable_python

from _helpers import create_item
from _legacy_squad import reopen, stamp_behind
from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: (id, key, value, declared by an override while the key is planted)
SHAPES = [
    ("declared-then-removed-from-the-override", "weight", True, True),
    ("never-declared", "hand_key", "keep-me", False),
    ("declared-with-a-kind-that-no-longer-matches", "tags", "a,b", False),
    ("declared-and-carried-to-a-type-that-does-not-declare-it", "tech", "go", False),
    ("named-like-a-json-only-key", "discussion", "not a discussion", False),
    ("a-nested-mapping", "nested", {"a": {"b": 1}}, False),
    ("a-list", "listy", ["a", "b"], False),
    ("an-explicit-null", "nothing", None, False),
    ("an-unquoted-date", "due", date(2026, 10, 20), False),
    ("an-unquoted-timestamp", "due", datetime(2026, 10, 20, 10, 0, tzinfo=UTC), False),
    ("a-mapping-with-a-non-string-key", "keyed", {1: "a"}, False),
    ("named-like-a-model-field-path", "path", "docs/spec.md", False),
    ("named-like-a-model-field-prefix", "prefix", "X", False),
]

#: Names a row or the model owns: the row keeps its own value for them.
JSON_ONLY = {"discussion", "path", "prefix"}


@dataclass
class Env:
    project: Any
    invoke: Any
    tmp_path: Path
    svc: Service
    host: Any
    other: Any
    key: str


#: A write path runs against the planted item and returns the item's id afterwards plus a
#: check that the path did what it names.
type Path_ = Callable[[Env], Awaitable[tuple[str, Callable[[Service], Awaitable[None]]]]]


async def _witness_description(svc: Service, item_id: str, text: str) -> None:
    assert (await svc.get(item_id)).description == text


async def _p_update(env: Env):
    await env.svc.update(env.host.id, description="touched")
    return env.host.id, lambda s: _witness_description(s, env.host.id, "touched")


async def _p_set_another(env: Env):
    target = "tech" if env.key == "tags" else "tags"
    await env.svc.update(env.host.id, set_attributes={target: "x"})
    expected: Any = ["x"] if target == "tags" else "x"

    async def check(s: Service) -> None:
        assert (await s.get(env.host.id)).attributes[target] == expected

    return env.host.id, check


async def _p_status(env: Env):
    target = env.svc.spec.workflow_for("guide").transitions[env.host.status][0]
    await env.svc.set_status(env.host.id, target)

    async def check(s: Service) -> None:
        assert (await s.get(env.host.id)).status == target

    return env.host.id, check


async def _p_comment(env: Env):
    await env.svc.comment(env.host.id, ["a recorded note"], as_slug="manager")

    async def check(s: Service) -> None:
        assert "a recorded note" in await s.read_discussion(env.host.id)

    return env.host.id, check


async def _p_body(env: Env):
    await env.svc.set_body(env.host.id, "A new body.")

    async def check(s: Service) -> None:
        assert "A new body." in await s.read_body(env.host.id)

    return env.host.id, check


async def _p_ref(env: Env):
    await env.svc.add_ref(env.host.id, env.other.id, kind="blocks")

    async def check(s: Service) -> None:
        assert (await s.get(env.host.id)).refs == [f"{env.other.id}:blocks"]

    return env.host.id, check


async def _p_subentity(env: Env):
    await env.svc.add_subtask(env.host.id, "child")
    await env.svc.set_subtask_status(env.host.id, "ST1", "InProgress")

    async def check(s: Service) -> None:
        (sub,) = (await s.get(env.host.id)).subentities
        assert (sub.local_id, sub.status) == ("ST1", "InProgress")

    return env.host.id, check


async def _p_retype(env: Env):
    result = await env.svc.retype(env.host.id, "contract")
    new_id = result.item.id

    async def check(s: Service) -> None:
        assert (await s.get(new_id)).type == "contract"

    return new_id, check


async def _p_rename_type(env: Env):
    await env.svc.rename_type("guide", "contract")
    new_id = next(i.id for i in await env.svc.list_items(item_type="contract"))

    async def check(s: Service) -> None:
        assert (await s.get(new_id)).type == "contract"

    return new_id, check


async def _p_renumber(env: Env):
    result = await env.svc.renumber(from_seq=env.host.sequence_id, onto=env.host.sequence_id + 500)
    new_id = result.remap[env.host.id]

    async def check(s: Service) -> None:
        assert (await s.get(new_id)).sequence_id != env.host.sequence_id

    return new_id, check


async def _p_import(env: Env):
    events = env.tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {"op": "update", "target": env.host.id, "as": "manager", "description": "imported"}
        )
        + "\n",
        encoding="utf-8",
    )
    result = await env.svc.import_events(events.read_text(encoding="utf-8"))
    assert result.plan.ok, result.plan.issues
    return env.host.id, lambda s: _witness_description(s, env.host.id, "imported")


async def _p_sync(env: Env):
    skipped = await env.svc.sync()
    assert not skipped, skipped
    return env.host.id, lambda s: _witness_synced(s, env.host.id)


async def _witness_synced(svc: Service, item_id: str) -> None:
    assert (await svc.get(item_id)).status == "Active"


async def _p_set_default(env: Env):
    await env.svc.set_default_role(env.host.id)

    async def check(s: Service) -> None:
        assert [r.slug for r in await s.roster() if r.is_default] == [env.host.slug]

    return env.host.id, check


async def _p_repair_then_write(env: Env):
    await env.svc.repair()
    await env.svc.update(env.host.id, description="after a repair")
    return env.host.id, lambda s: _witness_description(s, env.host.id, "after a repair")


async def _p_runner(env: Env):
    stamp_behind(env.project.root)
    run = await reopen(env.project.root).run_pending_migrations()

    async def check(_s: Service) -> None:
        assert [m.to_schema for m in run.applied] == ["0.16"]

    return env.host.id, check


#: (id, host type, path)
PATHS: list[tuple[str, str, Any]] = [
    ("update-another-field", "guide", _p_update),
    ("update-set-another-attribute", "guide", _p_set_another),
    ("status", "guide", _p_status),
    ("comment", "guide", _p_comment),
    ("body", "guide", _p_body),
    ("sub-entity-add-and-update", "task", _p_subentity),
    ("ref-add", "guide", _p_ref),
    ("retype", "guide", _p_retype),
    ("type-rename", "guide", _p_rename_type),
    ("renumber", "guide", _p_renumber),
    ("import", "guide", _p_import),
    ("sync-on-a-role", "role", _p_sync),
    ("set-default", "role", _p_set_default),
    ("repair-then-a-write", "guide", _p_repair_then_write),
    ("the-0.16-runner", "guide", _p_runner),
]


def _plant(svc: Service, item: Any, key: str, value: Any) -> None:
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    data, _ = split_frontmatter(text)
    data[key] = value
    path.write_text(replace_frontmatter(text, data), encoding="utf-8")


def _override(project: Any, item_type: str, *, declare: str | None) -> None:
    target = project.squad_dir / ".overrides" / "workflow.toml"
    if declare is None:
        target.unlink(missing_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# squads:override-base:{__version__}\n[items.{item_type}.attributes]\n"
            f'{declare} = {{ kind = "bool" }}\n',
            encoding="utf-8",
        )
    invalidate_squad_dir(project.squad_dir)


async def _host(svc: Service, item_type: str) -> Any:
    if item_type == "role":
        return await svc.activate_role("qa")
    return (await create_item(svc, item_type, "Planted host")).item


@pytest.mark.parametrize(("shape", "key", "value", "declared"), SHAPES, ids=[s[0] for s in SHAPES])
@pytest.mark.parametrize(("path_id", "host_type", "path"), PATHS, ids=[p[0] for p in PATHS])
async def test_a_write_keeps_a_key_it_did_not_target(
    project, invoke, tmp_path, path_id, host_type, path, shape, key, value, declared
) -> None:
    if declared:
        _override(project, host_type, declare=key)
    svc = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    host = await _host(svc, host_type)
    other = (await create_item(svc, "task", "Another item")).item
    _plant(svc, host, key, value)
    await svc.repair()
    if declared:
        _override(project, host_type, declare=None)
    svc = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    env = Env(project, invoke, tmp_path, svc, await svc.get(host.id), other, key)

    item_id, witness = await path(env)

    after = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    await witness(after)
    item = await after.get(item_id)
    stored, _ = split_frontmatter(project.squad_dir.joinpath(item.path).read_text("utf-8"))
    expected = to_jsonable_python(value)  # a date or timestamp is kept as its ISO string
    # A path that rewrites the frontmatter stores the ISO form; one that does not keeps the
    # file's own typed value. Either way the key is there and means the same thing.
    assert key in stored and to_jsonable_python(stored[key]) == expected, (
        "the key left the file or changed"
    )
    shown = await invoke(["show", item_id, "--json"])
    assert shown.exit_code == 0, shown.output
    row = json.loads(shown.output)
    if key in JSON_ONLY:
        assert row.get(key) != expected  # the row's own key keeps its meaning
    else:
        assert key in row and row[key] == expected, "the key left the --json row"
    rebuilt = await after.repair()
    assert rebuilt.db.get(item_id).attributes[key] == expected, "the key left the rebuilt index"  # type: ignore[union-attr]


# --------------------------------------------------------------------------- the controls


#: (id, a command that targets a declared attribute, expected stored value afterwards)
async def _control_set(svc: Service, item_id: str, tmp_path: Path) -> None:
    await svc.update(item_id, set_attributes={"tech": "rust"})


async def _control_unset_by_import(svc: Service, item_id: str, tmp_path: Path) -> None:
    events = tmp_path / "unset.jsonl"
    events.write_text(
        json.dumps({"op": "update", "target": item_id, "as": "manager", "unset_fields": ["tech"]})
        + "\n",
        encoding="utf-8",
    )
    result = await svc.import_events(events.read_text(encoding="utf-8"))
    assert result.plan.ok, result.plan.issues


CONTROLS = [
    ("set", _control_set, "rust"),
    ("unset-through-an-import", _control_unset_by_import, None),
]


@pytest.mark.parametrize(
    ("command", "expected"), [c[1:] for c in CONTROLS], ids=[c[0] for c in CONTROLS]
)
async def test_a_command_that_targets_a_key_does_change_it(
    project, tmp_path, svc, command, expected
) -> None:
    host = (await create_item(svc, "guide", "Planted host")).item
    _plant(svc, host, "tech", "go")
    await svc.repair()

    await command(svc, host.id, tmp_path)

    stored, _ = split_frontmatter(project.squad_dir.joinpath(host.path).read_text("utf-8"))
    assert stored.get("tech") == expected
