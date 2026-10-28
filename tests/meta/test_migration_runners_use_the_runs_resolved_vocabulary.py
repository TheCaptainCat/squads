"""Every migration runner reaches the index, and every other vocabulary question, under the one spec
and playbook the run resolved: no runner opens an ``IndexStore`` without a real ``spec=`` (it
would validate under the bundled vocabulary instead of the squad's own), and none resolves or
fetches a spec or playbook for itself."""

import ast
from pathlib import Path

import squads._migrations as migrations_pkg

_BANNED = frozenset(
    {
        "load_workflow_spec",
        "load_playbook",
        "bundled_spec",
        "get_playbook_spec",
        "get_active_spec",
        "open_service",
        "resolve_playbook",
        "Service",
        "PLAYBOOK",
    }
)

_MIGRATIONS_DIR = Path(migrations_pkg.__file__).parent

#: Frozen legacy-format reader behind the two oldest file-walking runners (which take paths):
#: it answers one question from the bundled vocabulary on purpose.
_EXEMPT: dict[str, frozenset[str]] = {"_meta_compat.py": frozenset({"bundled_spec"})}


def _index_store_names(tree: ast.AST) -> set[str]:
    names = {"IndexStore"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(a.asname for a in node.names if a.name == "IndexStore" and a.asname)
        elif (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Name)
            and node.value.id in names
        ):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _violations(source: str, *, allowed: frozenset[str] = frozenset()) -> list[str]:
    tree = ast.parse(source)
    banned = _BANNED - allowed
    store_names = _index_store_names(tree)
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found.extend(
                f"line {node.lineno}: imports {a.name}" for a in node.names if a.name in banned
            )
        elif isinstance(node, ast.Name) and node.id in banned:
            found.append(f"line {node.lineno}: references {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr in banned:
            found.append(f"line {node.lineno}: references {node.attr}")
        elif isinstance(node, ast.Name) and node.id in store_names and id(node) not in called:
            if not isinstance(node.ctx, ast.Store):
                found.append(f"line {node.lineno}: uses IndexStore other than by calling it")
        elif isinstance(node, ast.Call) and _callee_name(node) in store_names:
            spec = next((kw.value for kw in node.keywords if kw.arg == "spec"), None)
            if spec is None or (isinstance(spec, ast.Constant) and spec.value is None):
                found.append(f"line {node.lineno}: IndexStore(...) without a spec")
    return found


def _callee_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_the_scan_sees_each_kind_of_violation() -> None:
    planted = {
        "imports bundled_spec": "from squads._workflow import bundled_spec\n",
        "without a spec": "store = IndexStore(paths.index_path, paths.lock_path)\n",
        "references load_workflow_spec": "spec = loader.load_workflow_spec(squad_dir=d)\n",
        "references get_playbook_spec": "pb = get_playbook_spec()\n",
        "references Service": "svc = Service(paths)\n",
        "references open_service": "svc = open_service()\n",
        "a None spec": "store = IndexStore(a, b, spec=None)\n",
        "an aliased import": "from x import IndexStore as Store\nstore = Store(a, b)\n",
        "a rebinding": "cls = IndexStore\nstore = cls(a, b)\n",
        "a partial": "make = functools.partial(IndexStore, a, b)\n",
    }
    for label, source in planted.items():
        assert _violations(source), f"the scan missed {label}"
    assert _violations("store = IndexStore(a, b, spec=ctx.spec)\n") == []
    assert _violations("x = bundled_spec()\n", allowed=frozenset({"bundled_spec"})) == []
    assert _violations("x = get_playbook_spec()\n", allowed=frozenset({"bundled_spec"}))


def test_the_scan_walks_every_runner_module() -> None:
    assert len(list(_MIGRATIONS_DIR.rglob("*.py"))) >= 12


def test_no_migration_module_resolves_its_own_vocabulary_or_opens_an_unspecced_index() -> None:
    offenders = {
        path.name: hits
        for path in sorted(_MIGRATIONS_DIR.rglob("*.py"))
        if (
            hits := _violations(
                path.read_text(encoding="utf-8"), allowed=_EXEMPT.get(path.name, frozenset())
            )
        )
    }
    assert not offenders, offenders
