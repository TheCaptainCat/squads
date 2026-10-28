"""Fixtures for the `sq check` rule tests: `check_json` runs the report and records what it
found, `select_validators` writes the minimal override that enables a member, and at teardown a
test fails when a `breaches` declaration was not honoured by the report.
"""

import copy
import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from squads import __version__
from squads._workflow import bundled_spec
from squads._workflow._validator_names import (
    MULTI_SELECTION_VALIDATOR_NAMES,
    parse_validator_entry,
    validator_selection_key,
)
from tests import _check_surface as check_surface

type Issue = dict[str, str]
type Select = Callable[..., Path]


class CheckRun(NamedTuple):
    """One `sq check --json` run: the parsed issue array and the exit code."""

    issues: list[Issue]
    exit_code: int


@dataclass(frozen=True)
class Run:
    """What one run reported and which members carried a param in the override when it ran."""

    reported: frozenset[tuple[str, str]]
    params: dict[str, frozenset[str]]

    @property
    def rules(self) -> frozenset[str]:
        return frozenset(rule for rule, _ in self.reported)


@dataclass
class Observed:
    """The runs of a test, in order."""

    runs: list[Run] = field(default_factory=lambda: [])


@dataclass
class Selections:
    """The override `select_validators` has written: the entries and extra keys of each table, the
    override that was in the squad before the first call, and the params in effect now."""

    squad_dir: Path
    entries: dict[str, list[str]] = field(default_factory=lambda: {})
    extra: dict[str, dict[str, Any]] = field(default_factory=lambda: {})
    base: dict[str, Any] | None = None

    @property
    def path(self) -> Path:
        return self.squad_dir / ".overrides" / "workflow.toml"

    def params_in_override(self) -> dict[str, frozenset[str]]:
        """The params the override on disk selects now, by member."""
        if not self.path.exists():
            return {}
        try:
            doc = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            return {}  # a file that does not load selects nothing
        return _carried_params(doc)


def _declarations(node: pytest.Item) -> list[check_surface.Declaration]:
    """The declarations the `breaches` markers of *node* make; a marker that is not made of
    declaration literals fails the test."""
    declared: list[check_surface.Declaration] = []
    for marker in node.iter_markers("breaches"):
        parsed = [
            check_surface.parse_declaration(a) if isinstance(a, str) else None for a in marker.args
        ]
        if not marker.args or marker.kwargs or None in parsed:
            pytest.fail(
                f"breaches{marker.args!r} must be rule, rule:param or rule@level literals",
                pytrace=False,
            )
        declared += [d for d in parsed if d is not None]
    return declared


def _honouring_runs(runs: list[Run], rule: str, level: str | None) -> list[int]:
    """The indexes of the runs that reported *rule* (at *level* when given) after a run that did
    not report it at all."""
    return [
        i
        for i in range(1, len(runs))
        if rule not in runs[i - 1].rules
        and ((rule, level) in runs[i].reported if level else rule in runs[i].rules)
    ]


def _unhonoured(declared: list[check_surface.Declaration], seen: Observed) -> list[str]:
    """The declarations no run of the test honoured, each with the reason."""
    missing: list[str] = []
    for d in declared:
        text = f"{d.rule}@{d.level}" if d.level else d.rule + (":param" if d.param else "")
        runs = _honouring_runs(seen.runs, d.rule, d.level)
        if not runs:
            missing.append(f"{text} was not reported by a run after a run that did not report it")
        elif d.param:
            needed = 2 if d.rule in MULTI_SELECTION_VALIDATOR_NAMES else 1
            if not any(len(seen.runs[i].params.get(d.rule, ())) >= needed for i in runs):
                missing.append(
                    f"{text} needs {needed} param(s) selected before the run that reported it "
                    "and still in the override"
                )
    return missing


@pytest.fixture
def observed() -> Observed:
    """The runs made so far in this test."""
    return Observed()


@pytest.fixture
def selections(project) -> Selections:
    """The override state of this test's squad."""
    return Selections(project.squad_dir)


@pytest.fixture(autouse=True)
def _breaches_markers_need_check_json(request: pytest.FixtureRequest):  # pyright: ignore[reportUnusedFunction]  # autouse
    """Fail a test that declares `breaches` without the `check_json` that checks the claim."""
    if request.node.get_closest_marker("breaches") and "check_json" not in request.fixturenames:
        pytest.fail(
            "a test that declares `breaches` must run the report through `check_json`",
            pytrace=False,
        )


@pytest.fixture
def check_json(request: pytest.FixtureRequest, invoke: Any, observed: Observed, selections):
    """Run `sq check --json` and return its `CheckRun`, recording what it reported and which params
    were selected. Stderr must equal `stderr=` (empty by default); at teardown an undeclared
    `breaches` claim fails the test.
    """

    async def _run(*, stderr: str = "") -> CheckRun:
        result = await invoke(["check", "--json"])
        if result.stderr != stderr:
            pytest.fail(
                f"sq check --json wrote {result.stderr!r} to stderr, expected {stderr!r}",
                pytrace=False,
            )
        try:
            issues: list[Issue] = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"sq check --json printed no JSON: {result.output!r}", pytrace=False)
        reported = frozenset((i["rule"], i["level"]) for i in issues)
        observed.runs.append(Run(reported, selections.params_in_override()))
        return CheckRun(issues, result.exit_code)

    yield _run
    missing = _unhonoured(_declarations(request.node), observed)
    if missing:
        pytest.fail("breaches declares what no run showed: " + "; ".join(missing), pytrace=False)


def _validators(on: str | None, entries: list[str], existing: list[str] | None) -> list[str]:
    """The `validators` list to write: *existing* when the squad already has one, else the bundled
    list written out when an entry replaces a bundled one, else a splat of it; *entries* replace
    the entry with the same selection key or are appended."""
    spec = bundled_spec()
    bundled = list(spec.squad.validators if on is None else spec.items[on].validators)
    bundled_keys = {validator_selection_key(b) for b in bundled}
    if existing is not None:
        listed = list(existing)
    elif any(validator_selection_key(e) in bundled_keys for e in entries):
        listed = bundled
    else:
        scope = "squad" if on is None else f"items.{on}"
        listed = [f"$(*{scope}.validators)"] if bundled else []
    for entry in entries:
        key = validator_selection_key(entry)
        at = next((i for i, e in enumerate(listed) if validator_selection_key(e) == key), None)
        if at is None:
            listed.append(entry)
        else:
            listed[at] = entry
    return listed


def _value(value: Any) -> str:
    """A TOML value: string, bool, int, array or inline table."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_value(v) for v in value) + "]"  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k} = {_value(v)}" for k, v in value.items()) + " }"  # pyright: ignore[reportUnknownVariableType]
    return str(value)


def _dumps(table: dict[str, Any], path: str = "") -> str:
    """TOML text of *table*: scalars and arrays under the header, nested tables after it."""
    plain = {k: v for k, v in table.items() if not isinstance(v, dict)}
    nested = {k: v for k, v in table.items() if isinstance(v, dict)}
    out = ""
    if path and (plain or not nested):
        out += f"[{path}]\n"
    out += "".join(f"{k} = {_value(v)}\n" for k, v in plain.items())
    for key, child in nested.items():
        out += "\n" + _dumps(child, f"{path}.{key}" if path else key)  # pyright: ignore[reportUnknownArgumentType]
    return out


def _carried_params(doc: dict[str, Any]) -> dict[str, frozenset[str]]:
    """The params the validators lists of *doc* select, by member."""
    lists: list[list[str]] = []
    squad: dict[str, Any] = doc.get("squad", {})
    lists.append(squad.get("validators", []))
    lists += [t.get("validators", []) for t in doc.get("items", {}).values()]
    found: dict[str, set[str]] = {}
    for entry in (e for names in lists for e in names):
        bare, param, _ = parse_validator_entry(entry)
        if param is not None:
            found.setdefault(bare, set()).add(param)
    return {bare: frozenset(params) for bare, params in found.items()}


@pytest.fixture
def select_validators(selections: Selections) -> Select:
    """Return `select(*entries, on=None, **extra)`, which writes the `workflow.toml` override.

    Entries go in `[squad]` or on type `on`, and `extra` keys (`ref_rules=[...]`) into that table.
    Calls accumulate, an existing override is kept, and the bundled list is spliced in by
    reference or, when an entry replaces one of its members, written out.
    """
    path = selections.path

    def _select(*entries: str, on: str | None = None, **extra: Any) -> Path:
        if selections.base is None:
            try:
                selections.base = (
                    tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                )
            except tomllib.TOMLDecodeError as exc:
                pytest.fail(
                    f"select_validators cannot build on an override that is not TOML: {exc}"
                )
        table = "squad" if on is None else f"items.{on}"
        for entry in entries:
            known = selections.entries.setdefault(table, [])
            key = validator_selection_key(entry)
            known[:] = [e for e in known if validator_selection_key(e) != key] + [entry]
        selections.extra.setdefault(table, {}).update(extra)
        doc = copy.deepcopy(selections.base)
        for name, listed in selections.entries.items():
            owner = name.removeprefix("items.") if name != "squad" else None
            scope = (
                doc.setdefault("squad", {})
                if owner is None
                else (doc.setdefault("items", {}).setdefault(owner, {}))
            )
            scope.update(selections.extra.get(name, {}))
            scope["validators"] = _validators(owner, listed, scope.get("validators"))
        for name, keys in selections.extra.items():
            if name not in selections.entries:
                owner = name.removeprefix("items.")
                doc.setdefault("items", {}).setdefault(owner, {}).update(keys)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# squads:override-base:{__version__}\n\n" + _dumps(doc), encoding="utf-8")
        return path

    return _select
