"""A migration runner raises no message that names a command the schema gate refuses on a squad that
is behind, and imports neither the write seam's skew guard nor its message. The scan is scoped to
``raise`` because the rest of a runner's text describes steps taken after the run."""

import ast
import re
from pathlib import Path

import squads._migrations as migrations_pkg
from squads._api._ops import OPERATIONS

_DIR = Path(migrations_pkg.__file__).parent
_FORBIDDEN_NAMES = frozenset({"skew_message", "ensure_no_skew"})
_WORD = r"(<[^>\s]+>|[a-z][\w-]*)"
_COMMAND = re.compile(rf"\bsq {_WORD}(?: {_WORD})?")


#: The ``sq migrate`` command each operation serves.
_MIGRATE_COMMANDS = {
    "squad.migrate": "migrate up",
    "squad.repad": "migrate repad",
    "squad.rename-type": "migrate rename-type",
    "squad.rename-status": "migrate rename-status",
    "squad.rename-field": "migrate rename-field",
    "squad.rename-kind": "migrate rename-kind",
}
#: The ``sq migrate`` commands that read the package's own registry and make no call, so the
#: schema gate never applies to them.
_NO_CALL = frozenset({"migrate help", "migrate chlog"})


def _permitted_when_behind() -> set[str]:
    granted = {
        _MIGRATE_COMMANDS[op.name]
        for op in OPERATIONS
        if op.name in _MIGRATE_COMMANDS and op.grant is not None and op.grant.behind
    }
    return granted | _NO_CALL


def _refused_commands(text: str) -> list[str]:
    permitted = _permitted_when_behind()
    found: list[str] = []
    for first, second in _COMMAND.findall(text):
        path = f"{first} {second}" if first == "migrate" and second else first
        if path not in permitted:
            found.append(path)
    return found


def _strings_bound_to_names(tree: ast.AST) -> dict[str, list[str]]:
    bound: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            texts = [
                n.value
                for n in ast.walk(node.value)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.setdefault(target.id, []).extend(texts)
    return bound


def _violations(source: str) -> list[str]:
    tree = ast.parse(source)
    bound = _strings_bound_to_names(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            for sub in ast.walk(node):
                texts: list[str] = []
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    texts = [sub.value]
                elif isinstance(sub, ast.Name):
                    texts = bound.get(sub.id, [])
                found.extend(
                    f"line {node.lineno}: raises {c}" for t in texts for c in _refused_commands(t)
                )
        elif isinstance(node, ast.ImportFrom):
            found.extend(
                f"line {node.lineno}: imports {a.name}"
                for a in node.names
                if a.name in _FORBIDDEN_NAMES
            )
        elif isinstance(node, ast.Name | ast.Attribute):
            name = node.id if isinstance(node, ast.Name) else node.attr
            if name in _FORBIDDEN_NAMES:
                found.append(f"line {node.lineno}: uses {name}")
    return found


def test_the_scan_sees_each_kind_of_violation() -> None:
    assert _violations('raise SquadsError("run `sq repair` first")\n')
    assert _violations('raise SquadsError(f"widen it with `sq migrate repad {n}`")\n')
    assert _violations('raise SquadsError("see `sq workflow lint`")\n')
    assert _violations("from squads._itemfile import skew_message\n")
    assert _violations("ensure_no_skew(x)\n")
    assert _violations('raise SquadsError("then `sq <type> <n> status X --force`")\n')
    assert _violations('MSG = "run `sq repair`"\nraise SquadsError(MSG)\n')
    assert _violations('msg = "run `sq repair`"\nraise SquadsError(msg)\n')
    assert _violations("itf.skew_message(x)\n")
    assert _violations('raise SquadsError("re-run `sq migrate up`")\n') == []
    assert _violations('print("run `sq check` afterwards")\n') == []


def test_no_runner_raises_a_refused_command_or_uses_the_skew_guard() -> None:
    offenders = {
        path.name: hits
        for path in sorted(_DIR.rglob("*.py"))
        if (hits := _violations(path.read_text(encoding="utf-8")))
    }
    assert not offenders, offenders
