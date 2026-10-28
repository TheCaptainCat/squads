"""Every (command, parameter) pair of the live command tree, hidden commands included, is declared
by a ``covers`` marker under ``tests/cli/``, every marker names a pair the tree has, and every
leaf command with no parameter is declared by its key alone.

A marker counts only on a collected test that runs. The markers are read with ``ast``.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest
import typer

from squads._workflow import bundled_spec
from tests import _help_tree as help_tree
from tests._cli_surface import (
    EXCLUDED_PARAMS,
    Pair,
    Surface,
    declared_pairs,
    surface_of,
)
from tests._help_tree import command_nodes
from tests._marker_ast import marker_calls, string_arguments
from tests.meta._roots import REPO_ROOT

CLI_TESTS = REPO_ROOT / "tests" / "cli"


@dataclass(frozen=True)
class Declarations:
    """What the markers under ``tests/cli/`` declare, and the markers that cannot be read."""

    pairs: frozenset[Pair]
    unreadable: tuple[str, ...]
    ignored: tuple[str, ...] = ()


def read_declarations(sources: dict[str, str]) -> Declarations:
    """The pairs declared by the ``covers`` markers in *sources* (module name to source text).

    A marker on a function that is not collected, or on a test that carries a skip, skipif, xfail
    or slow mark (or in a module whose ``pytestmark`` does), declares nothing and is listed in
    ``ignored``.
    """
    pairs: set[Pair] = set()
    unreadable: list[str] = []
    ignored: list[str] = []
    for name, source in sorted(sources.items()):
        found = marker_calls(ast.parse(source), "covers")
        for call in found.running:
            arguments = string_arguments(call)
            if arguments is None:
                unreadable.append(f"{name}:{call.lineno}")
            else:
                pairs.update(declared_pairs(arguments))
        for call in found.ignored:
            (ignored if string_arguments(call) is not None else unreadable).append(
                f"{name}:{call.lineno}"
            )
    return Declarations(frozenset(pairs), tuple(unreadable), tuple(ignored))


def cli_test_sources(root: Path = CLI_TESTS) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root.parent.parent).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("test_*.py"))
    }


def problems(surface: Surface, declared: Declarations) -> list[str]:
    """Every way *declared* departs from *surface*, one line each."""
    required = surface.required
    found = [
        f"unreadable covers marker (arguments must be string literals): {u}"
        for u in declared.unreadable
    ]
    found += [
        f"marker on a test that does not run (not collected, or skipped, xfailed or slow): {i}"
        for i in declared.ignored
    ]
    found += [
        f"stale marker: {_show(pair)} is not a pair of the tree"
        for pair in sorted(declared.pairs - required, key=_order)
    ]
    undeclared = required - declared.pairs
    found += [f"undeclared: {_show(pair)}" for pair in sorted(undeclared, key=_order)]
    return found


def _order(pair: Pair) -> tuple[str, str]:
    return pair[0], pair[1] or ""


def _show(pair: Pair) -> str:
    key, param = pair
    return f"sq {key} {param}" if param else f"sq {key} (the command itself)"


def _surface() -> Surface:
    return surface_of(command_nodes(include_hidden=True), bundled_spec())


def test_every_parameter_of_the_tree_is_declared_and_no_marker_is_stale() -> None:
    declared = read_declarations(cli_test_sources())
    assert problems(_surface(), declared) == []


def test_the_exclusions_are_exactly_the_completion_options_each_with_a_reason() -> None:
    assert set(EXCLUDED_PARAMS) == {("", "--install-completion"), ("", "--show-completion")}
    assert all(reason.strip() for reason in EXCLUDED_PARAMS.values())


def test_the_excluded_options_are_listed_by_the_tree_and_left_out_of_the_surface() -> None:
    nodes = command_nodes(include_hidden=True)
    listed = {
        (("" if not n.path else " ".join(n.path)), p.opts[0])
        for n in nodes
        for p in n.command.params
    }
    assert set(EXCLUDED_PARAMS) <= listed
    assert not set(EXCLUDED_PARAMS) & _surface().pairs


def test_the_surface_folds_the_tree_onto_keys_without_vocabulary_or_the_address_segment() -> None:
    keys = {key for key, _ in _surface().required}
    assert "" in keys
    assert {"<type> update", "<type> <kind> update", "<type> add-<kind>", "<type> <kinds>"} <= keys
    assert {"<host> comment", "<host> comment edit", "create <type>", "role update"} <= keys
    assert not [k for k in keys if "_addr" in k]
    assert not [k for k in keys if k.split(" ")[0] in bundled_spec().non_roster_types()]


# ---------------------------------------------------------------------------- the checks bite

_SURFACE = Surface(frozenset({("a", "--x"), ("a", "--y"), ("b", "N")}), frozenset({"sync"}))


def _declare(*pairs: Pair) -> Declarations:
    return Declarations(frozenset(pairs), ())


_ALL = (("a", "--x"), ("a", "--y"), ("b", "N"), ("sync", None))


def test_a_complete_declaration_passes() -> None:
    assert problems(_SURFACE, _declare(*_ALL)) == []


def test_an_undeclared_pair_is_reported() -> None:
    declared = _declare(*_ALL[:1], *_ALL[2:])
    assert problems(_SURFACE, declared) == ["undeclared: sq a --y"]


def test_an_undeclared_parameterless_leaf_is_reported() -> None:
    assert problems(_SURFACE, _declare(*_ALL[:3])) == ["undeclared: sq sync (the command itself)"]


def test_a_stale_marker_is_reported() -> None:
    declared = _declare(*_ALL, ("a", "--gone"), ("gone", None))
    assert problems(_SURFACE, declared) == [
        "stale marker: sq a --gone is not a pair of the tree",
        "stale marker: sq gone (the command itself) is not a pair of the tree",
    ]


def test_a_key_marker_on_a_command_that_has_parameters_is_stale() -> None:
    declared = _declare(*_ALL, ("a", None))
    assert problems(_SURFACE, declared) == [
        "stale marker: sq a (the command itself) is not a pair of the tree"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('@pytest.mark.covers("a", "--x")\ndef test_x(): ...', {("a", "--x")}),
        ('@pytest.mark.covers("sync")\ndef test_x(): ...', {("sync", None)}),
        (
            '@pytest.mark.covers("a", "--x", "--y")\nasync def test_x(): ...',
            {("a", "--x"), ("a", "--y")},
        ),
        ('pytestmark = pytest.mark.covers("b", "N")\ndef test_x(): ...', {("b", "N")}),
        ('@pytest.mark.covers("")\ndef test_x(): ...', {("", None)}),
        ("@pytest.mark.slow\ndef test_x(): ...", set()),
    ],
)
def test_markers_are_read_without_importing_the_module(source: str, expected: set[Pair]) -> None:
    declared = read_declarations({"tests/cli/test_m.py": source})
    assert declared.pairs == expected
    assert declared.unreadable == ()


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ('KEY = "a"\n@pytest.mark.covers(KEY, "--x")\ndef test_x(): ...', 2),
        ('@pytest.mark.covers("a", f"--{1}")\ndef test_x(): ...', 1),
        ("@pytest.mark.covers()\ndef test_x(): ...", 1),
        ('@pytest.mark.covers("a", param="--x")\ndef test_x(): ...', 1),
    ],
)
def test_a_marker_that_is_not_made_of_string_literals_is_reported(source: str, line: int) -> None:
    declared = read_declarations({"tests/cli/test_m.py": source})
    assert declared.unreadable == (f"tests/cli/test_m.py:{line}",)
    assert declared.pairs == frozenset()


@pytest.mark.parametrize(
    "source",
    [
        '@pytest.mark.skip\n@pytest.mark.covers("a", "--x")\ndef test_x(): ...',
        '@pytest.mark.covers("a", "--x")\n@pytest.mark.skip(reason="r")\ndef test_x(): ...',
        '@pytest.mark.skipif(True, reason="r")\n@pytest.mark.covers("a", "--x")\ndef test_x(): ...',
        '@pytest.mark.xfail\n@pytest.mark.covers("a", "--x")\ndef test_x(): ...',
        '@pytest.mark.slow\n@pytest.mark.covers("a", "--x")\ndef test_x(): ...',
        (
            "@pytest.mark.skip\nclass TestM:\n"
            '    @pytest.mark.covers("a", "--x")\n    def test_x(self): ...'
        ),
        (
            "class TestM:\n    pytestmark = pytest.mark.skip\n"
            '    @pytest.mark.covers("a", "--x")\n    def test_x(self): ...'
        ),
        '@pytest.mark.covers("a", "--x")\ndef test_x(): ...\ndef test_x(): ...',
        '@pytest.mark.covers("a", "--x")\ndef helper(): ...',
        '@pytest.mark.covers("a", "--x")\ndef _test_x(): ...',
        'pytestmark = [pytest.mark.skip, pytest.mark.covers("a", "--x")]\ndef test_x(): ...',
        'pytestmark = pytest.mark.covers("a", "--x")\ndef helper(): ...',
        'pytestmark = pytest.mark.slow\n@pytest.mark.covers("a", "--x")\ndef test_x(): ...',
        'def helper():\n    return pytest.mark.covers("a", "--x")',
    ],
)
def test_a_marker_on_a_test_that_does_not_run_declares_nothing_and_is_reported(
    source: str,
) -> None:
    declared = read_declarations({"tests/cli/test_m.py": source})
    assert declared.pairs == frozenset()
    assert len(declared.ignored) == 1
    assert problems(Surface(frozenset(), frozenset()), declared) == [
        "marker on a test that does not run (not collected, or skipped, xfailed or slow): "
        f"{declared.ignored[0]}"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'class TestM:\n    @pytest.mark.covers("a", "--x")\n    def test_x(self): ...',
            {("a", "--x")},
        ),
        (
            '@pytest.mark.anyio\n@pytest.mark.covers("a", "--x")\nasync def test_x(): ...',
            {("a", "--x")},
        ),
        (
            'pytestmark = [pytest.mark.anyio, pytest.mark.covers("b", "N")]\ndef test_x(): ...',
            {("b", "N")},
        ),
    ],
)
def test_a_marker_on_a_collected_test_that_runs_declares_its_pairs(
    source: str, expected: set[Pair]
) -> None:
    declared = read_declarations({"tests/cli/test_m.py": source})
    assert declared.pairs == expected
    assert declared.ignored == ()


def _app_with_hidden_command() -> typer.Typer:
    app = typer.Typer()

    @app.command()
    def shown() -> None:  # pyright: ignore[reportUnusedFunction]
        ...

    @app.command(name="wipe", hidden=True)
    def wipe(  # pyright: ignore[reportUnusedFunction]
        everything: bool = typer.Option(False, "--everything"),
    ) -> None: ...

    return app


def test_a_hidden_command_and_its_parameters_are_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(help_tree, "app", _app_with_hidden_command())
    surface = surface_of(command_nodes(include_hidden=True), bundled_spec())
    assert ("wipe", "--everything") in surface.pairs
    declared = _declare(*(surface.required - {("wipe", "--everything")}))
    assert problems(surface, declared) == ["undeclared: sq wipe --everything"]


def test_a_hidden_command_is_left_out_of_the_visible_walk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(help_tree, "app", _app_with_hidden_command())
    surface = surface_of(command_nodes(), bundled_spec())
    assert not [pair for pair in surface.pairs if pair[0] == "wipe"]


def test_the_hidden_roster_removal_is_part_of_the_surface() -> None:
    required = _surface().required
    assert {("role rm", "--purge"), ("role rm", "--as")} <= required
    assert not [pair for pair in required if pair[0] in {"skill rm", "operator rm"}]
