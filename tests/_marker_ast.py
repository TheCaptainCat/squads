"""Reading a pytest marker out of test source with ``ast``, without importing the module.

A marker call counts only on a collected test that runs. The reader is static, so it cannot see a
mark reached through an alias or an import (``skip = pytest.mark.skip``, ``from pytest import
mark``), ``marks=`` on a parametrize case, or a skip raised at run time.
"""

import ast
from dataclasses import dataclass

#: The marks that keep a test from running in a default run.
NOT_RUN_MARKS = frozenset({"skip", "skipif", "xfail", "slow"})

type Function = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class MarkerCalls:
    """The calls of one marker in a module: those on a test that runs, and those that declare
    nothing (on a function that is not collected, a skipped test, or outside any test)."""

    running: tuple[ast.Call, ...]
    ignored: tuple[ast.Call, ...]


def marks(expressions: list[ast.expr]) -> list[tuple[str, ast.Call | None]]:
    """The ``pytest.mark.<name>`` marks among *expressions*, each with its call when it is one."""
    found: list[tuple[str, ast.Call | None]] = []
    for expression in expressions:
        call = expression if isinstance(expression, ast.Call) else None
        target = call.func if call else expression
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Attribute)
            and target.value.attr == "mark"
        ):
            found.append((target.attr, call))
    return found


@dataclass(frozen=True)
class CollectedTest:
    """A test pytest collects: its function and the ``Test*`` class that holds it, if any."""

    function: Function
    owner: ast.ClassDef | None = None


def _test_methods(node: ast.ClassDef) -> list[Function]:
    return [
        m
        for m in node.body
        if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef) and m.name.startswith("test")
    ]


def collected_tests(tree: ast.Module) -> list[CollectedTest]:
    """The tests pytest collects from *tree*: ``test*`` functions, and the ``test*`` methods of
    ``Test*`` classes, in source order."""
    found: list[CollectedTest] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            found += [CollectedTest(m, node) for m in _test_methods(node)]
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
            "test"
        ):
            found.append(CollectedTest(node))
    return found


def _shadowed(tests: list[CollectedTest]) -> set[int]:
    """The ids of the tests a later definition of the same name in the same scope replaces."""
    last = {(id(t.owner), t.function.name): t for t in tests}
    return {id(t.function) for t in tests if last[(id(t.owner), t.function.name)] is not t}


def module_marks(tree: ast.Module) -> list[tuple[str, ast.Call | None]]:
    """The marks a module-level ``pytestmark`` assignment carries."""
    return _pytestmark(tree.body)


def _pytestmark(body: list[ast.stmt]) -> list[tuple[str, ast.Call | None]]:
    found: list[tuple[str, ast.Call | None]] = []
    for node in body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            value = node.value
            items = value.elts if isinstance(value, ast.List | ast.Tuple) else [value]
            found += marks(items)
    return found


def is_mark_call(node: ast.AST, name: str) -> bool:
    """Whether *node* is a ``pytest.mark.<name>(...)`` call."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "mark"
    )


def marker_calls(tree: ast.Module, name: str) -> MarkerCalls:
    """Every ``pytest.mark.<name>(...)`` call in *tree*, split by whether its test runs.

    A test does not run when it, its class (decorator or class-level ``pytestmark``) or its module
    carries a skip, skipif, xfail or slow mark, or when a later definition replaces it.
    """
    module = module_marks(tree)
    module_runs = not NOT_RUN_MARKS & {m for m, _ in module}
    claimed: set[int] = set()
    running: list[ast.Call] = []
    ignored: list[ast.Call] = []

    def take(call: ast.Call, counts: bool) -> None:
        claimed.add(id(call))
        (running if counts else ignored).append(call)

    tests = collected_tests(tree)
    shadowed = _shadowed(tests)
    for test in tests:
        own = marks(test.function.decorator_list)
        held = marks(test.owner.decorator_list) + _pytestmark(test.owner.body) if test.owner else []
        runs = (
            module_runs
            and id(test.function) not in shadowed
            and not NOT_RUN_MARKS & {m for m, _ in own + held}
        )
        for mark, call in own:
            if mark == name and call is not None:
                take(call, runs)
    for mark, call in module:
        if mark == name and call is not None:
            take(call, module_runs and bool(tests))
    for owner in {t.owner for t in tests if t.owner is not None}:
        held = marks(owner.decorator_list) + _pytestmark(owner.body)
        for mark, call in held:
            if mark == name and call is not None:
                take(call, module_runs and not NOT_RUN_MARKS & {m for m, _ in held})
    ignored += [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and is_mark_call(node, name) and id(node) not in claimed
    ]
    return MarkerCalls(tuple(running), tuple(ignored))


def string_arguments(call: ast.Call) -> tuple[str, ...] | None:
    """The literal string arguments of a marker call, ``None`` when any is not one, when the call
    has keywords, or when it has no argument."""
    values = [
        a.value for a in call.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
    ]
    if len(values) != len(call.args) or call.keywords or not values:
        return None
    return tuple(values)
