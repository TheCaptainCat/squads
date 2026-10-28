"""Every `sq check` rule, member parameter and selectable level is declared by a `breaches` marker.

The required set is derived in `tests/_check_surface.py`.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests._check_surface import (
    PARAM,
    parse_declaration,
    required_declarations,
    required_param_members,
)
from tests._marker_ast import marker_calls, string_arguments
from tests.meta._roots import REPO_ROOT

CHECK_TESTS = REPO_ROOT / "tests" / "check"


@dataclass(frozen=True)
class Declarations:
    """What the markers under ``tests/check/`` declare, and the markers that cannot be read."""

    declared: frozenset[str]
    unreadable: tuple[str, ...]
    ignored: tuple[str, ...] = ()
    markers: tuple[frozenset[str], ...] = ()


def read_declarations(sources: dict[str, str]) -> Declarations:
    """The declarations of the ``breaches`` markers in *sources* (module name to source text).

    A marker on a function that is not collected, or on a test that carries a skip, skipif, xfail
    or slow mark (or in a module whose ``pytestmark`` does), declares nothing and is listed in
    ``ignored``; an argument that is not one of the three declaration forms is ``unreadable``.
    """
    declared: set[str] = set()
    unreadable: list[str] = []
    ignored: list[str] = []
    markers: list[frozenset[str]] = []
    for name, source in sorted(sources.items()):
        found = marker_calls(ast.parse(source), "breaches")
        for call in found.running + found.ignored:
            arguments = string_arguments(call)
            where = f"{name}:{call.lineno}"
            if arguments is None or any(parse_declaration(a) is None for a in arguments):
                unreadable.append(where)
            elif call in found.running:
                declared.update(arguments)
                markers.append(frozenset(arguments))
            else:
                ignored.append(where)
    return Declarations(frozenset(declared), tuple(unreadable), tuple(ignored), tuple(markers))


def check_test_sources(root: Path = CHECK_TESTS) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root.parent.parent).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("test_*.py"))
    }


def problems(
    required: frozenset[str],
    declared: Declarations,
    paired: frozenset[str] = frozenset(),
) -> list[str]:
    """Every way *declared* departs from *required*, one line each."""
    found = [
        f"unreadable breaches marker (arguments must be declaration literals): {u}"
        for u in declared.unreadable
    ]
    found += [
        f"marker on a test that does not run (not collected, or skipped, xfailed or slow): {i}"
        for i in declared.ignored
    ]
    found += [
        f"{member} and {member}{PARAM} must be declared on one marker: {sorted(marker)}"
        for marker in declared.markers
        for member in sorted(paired)
        if len({member, f"{member}{PARAM}"} & marker) == 1
    ]
    found += [f"stale marker: {d} is not required" for d in sorted(declared.declared - required)]
    found += [f"undeclared: {d}" for d in sorted(required - declared.declared)]
    return found


def test_every_check_rule_is_declared_and_no_marker_is_stale() -> None:
    declared = read_declarations(check_test_sources())
    assert problems(required_declarations(), declared, required_param_members()) == []


# ---------------------------------------------------------------------------- the checks bite

_REQUIRED = frozenset({"a", "b", "b:param", "b@error"})


def _declare(*names: str) -> Declarations:
    return Declarations(frozenset(names), (), (), (frozenset(names),))


def test_a_complete_declaration_passes() -> None:
    assert problems(_REQUIRED, _declare(*_REQUIRED)) == []


@pytest.mark.parametrize("missing", sorted(_REQUIRED))
def test_an_undeclared_rule_param_or_level_is_reported(missing: str) -> None:
    declared = _declare(*(_REQUIRED - {missing}))
    assert problems(_REQUIRED, declared) == [f"undeclared: {missing}"]


def test_a_stale_marker_is_reported() -> None:
    declared = _declare(*_REQUIRED, "gone", "b@warn")
    assert problems(_REQUIRED, declared) == [
        "stale marker: b@warn is not required",
        "stale marker: gone is not required",
    ]


def test_a_required_param_member_and_its_param_case_on_two_markers_are_reported() -> None:
    declared = Declarations(
        frozenset({"m", "m:param"}), (), (), (frozenset({"m"}), frozenset({"m:param"}))
    )
    assert problems(frozenset({"m", "m:param"}), declared, frozenset({"m"})) == [
        "m and m:param must be declared on one marker: ['m']",
        "m and m:param must be declared on one marker: ['m:param']",
    ]


def test_a_required_param_member_and_its_param_case_on_one_marker_pass() -> None:
    declared = _declare("m", "m:param")
    assert problems(frozenset({"m", "m:param"}), declared, frozenset({"m"})) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('@pytest.mark.breaches("a")\ndef test_x(): ...', {"a"}),
        (
            '@pytest.mark.breaches("a", "b:param", "b@warn")\nasync def test_x(): ...',
            {"a", "b:param", "b@warn"},
        ),
        ('pytestmark = pytest.mark.breaches("a")\ndef test_x(): ...', {"a"}),
        (
            'class TestM:\n    @pytest.mark.breaches("a")\n    def test_x(self): ...',
            {"a"},
        ),
        ("@pytest.mark.slow\ndef test_x(): ...", set()),
        ('@pytest.mark.breaches("a")\nclass TestM:\n    def test_x(self): ...', {"a"}),
        ('@pytest.mark.breaches("a")\ndef test_x(): ...\ndef test_y(): ...', {"a"}),
    ],
)
def test_markers_are_read_without_importing_the_module(source: str, expected: set[str]) -> None:
    declared = read_declarations({"tests/check/test_m.py": source})
    assert declared.declared == expected
    assert declared.unreadable == ()
    assert declared.ignored == ()


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ('KEY = "a"\n@pytest.mark.breaches(KEY)\ndef test_x(): ...', 2),
        ('@pytest.mark.breaches("a", f"b{1}")\ndef test_x(): ...', 1),
        ("@pytest.mark.breaches()\ndef test_x(): ...", 1),
        ('@pytest.mark.breaches("a", level="b")\ndef test_x(): ...', 1),
        ('@pytest.mark.breaches("a:b")\ndef test_x(): ...', 1),
        ('@pytest.mark.breaches("a@")\ndef test_x(): ...', 1),
        ('@pytest.mark.breaches("a:param@warn")\ndef test_x(): ...', 1),
        ('@pytest.mark.breaches("A")\ndef test_x(): ...', 1),
    ],
)
def test_a_marker_that_is_not_a_declaration_literal_is_reported(source: str, line: int) -> None:
    declared = read_declarations({"tests/check/test_m.py": source})
    assert declared.unreadable == (f"tests/check/test_m.py:{line}",)
    assert declared.declared == frozenset()


@pytest.mark.parametrize(
    "source",
    [
        '@pytest.mark.skip\n@pytest.mark.breaches("a")\ndef test_x(): ...',
        '@pytest.mark.breaches("a")\n@pytest.mark.skip(reason="r")\ndef test_x(): ...',
        '@pytest.mark.skipif(True, reason="r")\n@pytest.mark.breaches("a")\ndef test_x(): ...',
        '@pytest.mark.xfail\n@pytest.mark.breaches("a")\ndef test_x(): ...',
        '@pytest.mark.slow\n@pytest.mark.breaches("a")\ndef test_x(): ...',
        (
            "@pytest.mark.skip\nclass TestM:\n"
            '    @pytest.mark.breaches("a")\n    def test_x(self): ...'
        ),
        (
            "class TestM:\n    pytestmark = pytest.mark.skip\n"
            '    @pytest.mark.breaches("a")\n    def test_x(self): ...'
        ),
        '@pytest.mark.breaches("a")\ndef test_x(): ...\ndef test_x(): ...',
        '@pytest.mark.skip\n@pytest.mark.breaches("a")\nclass TestM:\n    def test_x(self): ...',
        '@pytest.mark.breaches("a")\ndef helper(): ...',
        '@pytest.mark.breaches("a")\ndef _test_x(): ...',
        'pytestmark = [pytest.mark.skip, pytest.mark.breaches("a")]\ndef test_x(): ...',
        'pytestmark = pytest.mark.breaches("a")\ndef helper(): ...',
        'pytestmark = pytest.mark.slow\n@pytest.mark.breaches("a")\ndef test_x(): ...',
        'def helper():\n    return pytest.mark.breaches("a")',
    ],
)
def test_a_marker_on_a_test_that_does_not_run_declares_nothing_and_is_reported(
    source: str,
) -> None:
    declared = read_declarations({"tests/check/test_m.py": source})
    assert declared.declared == frozenset()
    assert len(declared.ignored) == 1
    assert problems(frozenset(), declared) == [
        "marker on a test that does not run (not collected, or skipped, xfailed or slow): "
        f"{declared.ignored[0]}"
    ]
