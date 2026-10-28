"""The index rebuild that runs before any migration resolves no vocabulary: its module imports
nothing from the packages that hold or serve a spec, and no function in it takes a
``WorkflowSpec`` or ``PlaybookSpec``. A static, import-level scan: it cannot see a spec reached
through a module the rebuild imports.
"""

import ast
from pathlib import Path

import squads._index._reconcile as reconcile

_FORBIDDEN = (
    "squads._workflow",
    "squads._interactions",
    "squads._views",
    "squads._specs",
    "squads._services",
)
_SPEC_TYPES = frozenset({"WorkflowSpec", "PlaybookSpec"})


def _problems(source: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(_FORBIDDEN):
                found.append(f"line {node.lineno}: imports {node.module}")
            elif node.module == "squads" and any(
                f"squads.{a.name}".startswith(_FORBIDDEN) for a in node.names
            ):
                found.append(f"line {node.lineno}: imports a forbidden package from squads")
        elif isinstance(node, ast.Import):
            found.extend(
                f"line {node.lineno}: imports {a.name}"
                for a in node.names
                if a.name.startswith(_FORBIDDEN)
            )
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            found.extend(
                f"line {node.lineno}: {node.name} takes a spec"
                for a in args
                if a.annotation is not None and _SPEC_TYPES & _names(a.annotation)
            )
    return found


def _names(annotation: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(annotation) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(annotation) if isinstance(n, ast.Attribute)
    }


def test_the_scan_sees_each_kind_of_violation() -> None:
    assert _problems("from squads._workflow import bundled_spec\n")
    assert _problems("from squads._services._service import Service\n")
    assert _problems("import squads._interactions\n")
    assert _problems("from squads import _views\n")
    assert _problems("def f(spec: WorkflowSpec) -> None: ...\n")
    assert _problems("async def f(*, pb: 'x.PlaybookSpec | None') -> None: ...\n") == []
    assert _problems("async def f(*, pb: x.PlaybookSpec | None) -> None: ...\n")
    assert _problems("from squads._index._store import IndexStore\ndef f(a: int): ...\n") == []


def test_the_rebuild_module_imports_no_vocabulary_and_takes_no_spec() -> None:
    source = Path(reconcile.__file__).read_text(encoding="utf-8")
    assert _problems(source) == []
