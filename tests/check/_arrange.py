"""Arrangement helpers for the `sq check` rule tests: drive the CLI to build a squad state, and edit
an item file then re-index only for the states the create and update gate refuses.

An item is addressed by the id `create` returned, never by a literal number or path.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from squads import __version__
from squads import _clock as clock
from squads._overrides._manifest import artifact_changed_since, known_index_versions
from squads._paths import SquadPaths
from squads._spec_documents import resolve_workflow
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec


def issue(rule: str, level: str, item: str, message: str) -> dict[str, str]:
    """The issue object `sq check --json` prints."""
    return {"rule": rule, "level": level, "item": item, "message": message}


async def ok(invoke: Any, *args: str) -> Any:
    """Run `sq *args`, assert it exits 0 and return the result."""
    result = await invoke(list(args))
    assert result.exit_code == 0, result.output
    return result


def active_spec(project: SquadPaths) -> WorkflowSpec:
    """The workflow spec of the squad, with its override applied."""
    return resolve_workflow(project.squad_dir)


def address(item_id: str, spec: WorkflowSpec | None = None) -> list[str]:
    """The `sq` words that address *item_id*: its type's name and its number. The type resolves
    from the bundled spec unless *spec* is given, as it must be for a type an override adds."""
    prefix, number = item_id.rsplit("-", 1)
    return [(spec or bundled_spec()).prefix_to_type[prefix], str(int(number))]


async def activate(invoke: Any, *slugs: str) -> None:
    """Activate the roles *slugs*, so the types they author report no missing author."""
    for slug in slugs:
        await ok(invoke, "role", "activate", slug)


async def create(
    invoke: Any,
    item_type: str,
    title: str,
    author: str,
    *,
    parent: str | None = None,
    desc: str | None = None,
) -> str:
    """Create an item through the CLI and return its id."""
    args = ["create", item_type, title, "--author", author, "--json"]
    if parent is not None:
        args += ["--parent", parent]
    if desc is not None:
        args += ["--desc", desc]
    result = await ok(invoke, *args)
    return json.loads(result.output)["id"]


async def add_roster(invoke: Any, kind: str, name: str, *options: str) -> str:
    """Run `sq <kind> add <name> *options` (an operator or a skill) and return the id it created,
    read from the human output because `operator add`, `skill add` and `role add` have no `--json`;
    take the id from `--json` wherever a command offers it."""
    result = await ok(invoke, kind, "add", name, *options)
    found = re.search(r"\b[A-Z]+-\d+\b", result.output)
    assert found, result.output
    return found.group()


async def update(invoke: Any, item_id: str, *args: str) -> None:
    """Run `sq <type> <n> update *args`."""
    await ok(invoke, *address(item_id), "update", *args)


async def set_status(invoke: Any, item_id: str, *statuses: str) -> None:
    """Move the item through *statuses* in order, each step through the CLI."""
    for status in statuses:
        await update(invoke, item_id, "--status", status)


async def write_body(invoke: Any, item_id: str, text: str) -> None:
    """Set the item's body through the CLI."""
    await ok(invoke, *address(item_id), "body", "-m", text)


async def add_ref(invoke: Any, item_id: str, target: str, kind: str | None = None) -> None:
    """Add the ref *item_id* → *target* (of *kind* when given) through the CLI."""
    await ok(invoke, *address(item_id), "ref", "add", target, *(["--kind", kind] if kind else []))


async def remove_ref(invoke: Any, item_id: str, target: str) -> None:
    """Remove the ref *item_id* → *target* through the CLI."""
    await ok(invoke, *address(item_id), "ref", "rm", target)


async def repair(invoke: Any) -> None:
    """Re-index the item files, as the damaged-squad fixture does after a file write."""
    await ok(invoke, "repair")


def write_override(
    project: SquadPaths, name: str, text: str, *, stamp: str | None = __version__
) -> None:
    """Write `.overrides/<name>` in the squad with *text*, replacing the file when it exists. A
    `.toml` file is stamped with the base version *stamp* (the running one by default; `None`
    writes none), so an older or missing stamp is arranged by passing it."""
    path = project.squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = f"# squads:override-base:{stamp}\n\n" if path.suffix == ".toml" and stamp else ""
    path.write_text(marker + text, encoding="utf-8")


def edit_config(project: SquadPaths, old: str, new: str) -> None:
    """Replace *old* with *new* in `.squads.toml`; *old* must occur exactly once."""
    text = project.config_path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times in .squads.toml"
    project.config_path.write_text(text.replace(old, new), encoding="utf-8")


async def role_id(invoke: Any, slug: str) -> str:
    """The id of the activated role filed under *slug*."""
    result = await ok(invoke, "role", slug, "show", "--json")
    return json.loads(result.output)["id"]


async def at(invoke: Any, when: datetime, *args: str) -> Any:
    """Run `sq *args` recording *when* as the time of the change, and assert it exits 0."""
    return await ok(invoke, "--at", clock.iso(when), *args)


def stale_base(key: str) -> str:
    """A released version whose bundled artifact *key* differs from the installed one."""
    return next(v for v in known_index_versions() if artifact_changed_since(key, v))


def unchanged_base(key: str) -> str:
    """A released version older than the installed one whose bundled artifact *key* is the same as
    the installed one, or unrecorded."""
    return next(
        v for v in known_index_versions() if v != __version__ and not artifact_changed_since(key, v)
    )


def item_path(project: SquadPaths, item_id: str) -> Path:
    """The file of the item *item_id*."""
    prefix, number = item_id.rsplit("-", 1)
    (path,) = project.squad_dir.rglob(f"{prefix}-{int(number):06d}-*.md")
    return path


def edit_item_file(project: SquadPaths, item_id: str, old: str, new: str) -> None:
    """Replace *old* with *new* in the item's file, byte for byte: the file keeps its own line
    ending, and *old* and *new* are written with `\\n`. *old* must occur exactly once."""
    path = item_path(project, item_id)
    data = path.read_bytes()
    if b"\r\n" in data:
        old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
    assert data.count(old.encode()) == 1, f"{old!r} does not occur once in {path.name}"
    path.write_bytes(data.replace(old.encode(), new.encode()))


def drop_frontmatter_line(project: SquadPaths, item_id: str, key: str) -> None:
    """Remove the item's `<key>: …` frontmatter line, whatever its value."""
    path = item_path(project, item_id)
    lines = path.read_bytes().splitlines(keepends=True)
    kept = [line for line in lines if not line.startswith(f"{key}:".encode())]
    assert len(kept) == len(lines) - 1, f"{path.name} has no single `{key}:` line"
    path.write_bytes(b"".join(kept))


def fresh_number(project: SquadPaths) -> int:
    """A sequence number no item file in the squad carries."""
    numbers = [
        int(found[1])
        for path in project.squad_dir.rglob("*.md")
        if (found := re.search(r"-(\d{6})-", path.name))
    ]
    return max(numbers) + 1


def copy_item_file(
    project: SquadPaths,
    item_id: str,
    *,
    number: int | None = None,
    as_type: str | None = None,
    slug: str = "copy",
) -> tuple[str, Path]:
    """Copy the item's file beside the original as an item of *as_type* (its own type by default)
    numbered *number* (its own by default), under a file name ending in *slug*; return the copy's
    id and path. The copy is a file only: the index does not know it."""
    spec = active_spec(project)
    src_prefix, src_number = item_id.rsplit("-", 1)
    src_type = spec.prefix_to_type[src_prefix]
    dst_type = as_type or src_type
    dst_prefix = spec.items[dst_type].prefix
    dst_number = number if number is not None else int(src_number)
    dst_id = f"{dst_prefix}-{dst_number}"
    data = item_path(project, item_id).read_bytes()
    for old, new in (
        (f"id: {item_id}", f"id: {dst_id}"),
        (f"sequence_id: {int(src_number)}", f"sequence_id: {dst_number}"),
        (f"type: {src_type}", f"type: {dst_type}"),
    ):
        assert data.count(old.encode()) == 1, old
        data = data.replace(old.encode(), new.encode())
    folder = project.folder_for(dst_type, spec)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{dst_prefix}-{dst_number:06d}-{slug}.md"
    path.write_bytes(data)
    return dst_id, path
