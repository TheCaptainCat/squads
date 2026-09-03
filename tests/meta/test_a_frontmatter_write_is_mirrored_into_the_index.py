"""Repo-hygiene gate: a service that writes an item's frontmatter commits the same item to the
index, unless it is on a named list of writers that deliberately do not.

Invariant 1 says the frontmatter is the source of truth and ``.squads.json`` is a rebuildable
index. It does not say the index may disagree with it indefinitely — and nearly everything that
reads a squad reads the index. ``sync``'s catalog merge is where that bit: it wrote a project
role override's title (and model, and mission) onto the role item's ``.md`` and stopped there,
so ``roster()`` — which both backends compile ``CLAUDE.md`` and ``AGENTS.md`` from, off the
index — kept rendering the bundled value. Durable and invisible at the same time, with
``sq check`` clean the whole way, until some unrelated ``sq repair`` rebuilt the index and the
*next* sync changed the generated roster for no visible reason.

Structurally, a write is mirrored when it happens inside a transaction. Two shapes count:
opening one (``async with self.store.transaction()``) and being handed an already-open one
(a ``db`` parameter — the mutation cores the mixins share). Anything else must be listed in
:data:`_UNMIRRORED_BY_DESIGN` with the reason, which is the point: the list is short, and
adding to it is a decision rather than an oversight.
"""

import ast
from pathlib import Path

_WRITER = "update_frontmatter"

#: Writers that persist to the ``.md`` without mirroring into the index, each with the reason
#: it is sound. Keyed ``module::function``.
#:
#: Empty today: the one writer that used to live here (the role's resolved-skills cache,
#: `_base.py::_refresh_role_skills_extra`) is gone along with the cache it maintained -- see
#: `test_the_allowlist_names_only_writers_that_still_exist` below, which is exactly the guard
#: that would have caught a stale entry left pointing at it.
_UNMIRRORED_BY_DESIGN: dict[str, str] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _opens_a_transaction(func: ast.AST) -> bool:
    for node in ast.walk(func):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            call = item.context_expr
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "transaction"
            ):
                return True
    return False


def _takes_an_open_transaction(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    args = func.args
    names = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    return "db" in names


def _calls_the_writer(func: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == _WRITER)
            or (isinstance(node.func, ast.Attribute) and node.func.attr == _WRITER)
        )
        for node in ast.walk(func)
    )


def _offenders() -> list[str]:
    services = _repo_root() / "src" / "squads" / "_services"
    found: list[str] = []
    for path in sorted(services.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _calls_the_writer(func):
                continue
            label = f"{path.name}::{func.name}"
            if label in _UNMIRRORED_BY_DESIGN:
                continue
            if _opens_a_transaction(func) or _takes_an_open_transaction(func):
                continue
            found.append(label)
    return found


def test_every_frontmatter_writer_either_commits_or_is_named() -> None:
    offenders = _offenders()
    assert not offenders, (
        f"{offenders} write item frontmatter without an index commit — the index will lag on "
        "whatever they persist, and every roster/list/generated-file reader goes through the "
        "index. Wrap the write in `self.store.transaction()` and `db.add(item)` (markdown "
        "first, commit last), or add an entry to _UNMIRRORED_BY_DESIGN saying why not."
    )


def test_the_allowlist_names_only_writers_that_still_exist() -> None:
    """A stale exemption is how this guard would quietly stop guarding."""
    services = _repo_root() / "src" / "squads" / "_services"
    live = {
        f"{path.name}::{func.name}"
        for path in services.glob("*.py")
        for func in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) and _calls_the_writer(func)
    }
    stale = sorted(set(_UNMIRRORED_BY_DESIGN) - live)
    assert not stale, f"_UNMIRRORED_BY_DESIGN names writers that no longer exist: {stale}"
