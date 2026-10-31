"""Durable enforcement that the CLI test harness resets *every* per-request ambient value a real
process establishes fresh but a fixture can pre-seed as a side effect of its own setup."""

import ast
from collections.abc import Iterator, Sequence
from pathlib import Path

#: module-level ContextVar declarations judged safe by construction and carved out of the
#: candidate walk, with the reason recorded — this judgment is semantic ("is it rebound/restored
#: before it can leak into a fixture's ambient context"), not syntactic, so it cannot be derived
#: from the walk itself the way the mutable-state guard's ALLOWLIST can; a change at any of these
#: call sites needs a human to re-read this comment, not just a green run.
CONTEXTVAR_EXEMPTIONS: dict[str, frozenset[str]] = {
    "src/squads/_context.py": frozenset(
        {
            # RequestContext's own var. main_callback binds one freshly-computed instance every
            # invocation (every field recomputed, not merged from what's ambient) — see
            # _context.py's and _cli/__init__.py's own docstrings. Safe by construction.
            "_context_var",
        }
    ),
    "src/squads/_daemon/_proxies.py": frozenset(
        {
            # Set at the start of a served command on the worker thread it runs on, whose context
            # is a copy: it ends with that thread's call and is never read by another request.
            "CURRENT",
        }
    ),
    "src/squads/_index/_store.py": frozenset(
        {
            # set(...)/reset(token) paired in the same try/finally (IndexStore.transaction()) —
            # never survives past the call that opened it.
            "_active_transaction",
            # Same enter_read_scope()/exit_read_scope() token-pairing discipline.
            "_read_scope",
            # set(...)/reset(token) paired in the same try/finally (IndexStore.exclusive()).
            "_exclusive_holder",
        }
    ),
}

#: The closed set of ambient values a real `sq` process establishes fresh that
#: tests/conftest.py's `invoke` fixture must reset per-call. Verified two ways below: against a
#: static re-derivation from src/squads (this file must find no more, no less), and against
#: tests/conftest.py's own `_AMBIENT_RESET_TARGETS` (the registry must describe what the
#: harness actually does).
RESET_TARGETS: dict[str, frozenset[str]] = {}


# ---------------------------------------------------------------------------------- the scan
# Mirrors test_no_unallowlisted_module_level_mutable_state.py's detector shape (construct 1 only
# — a `global` statement plays no part in whether something is a *ContextVar*, so construct 2 is
# not reused here).

_MUTABLE_FACTORY_NAMES = frozenset(
    {"dict", "list", "set", "defaultdict", "OrderedDict", "Counter", "deque"}
)


def _call_target_name(func: ast.expr) -> str | None:
    """The called name for a bare call (``f(...)``) or a qualified one (``mod.f(...)``)."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_mutable_binding(value: ast.expr) -> bool:
    if isinstance(value, ast.Dict | ast.List | ast.Set | ast.DictComp | ast.ListComp | ast.SetComp):
        return True
    return isinstance(value, ast.Call) and _call_target_name(value.func) in _MUTABLE_FACTORY_NAMES


def _target_bindings(target: ast.expr, value: ast.expr) -> list[tuple[str, ast.expr]]:
    """The (name, value) pairs one assignment *target* binds. A bare ``ast.Name`` binds the whole
    value; a tuple/list target destructures elementwise against a tuple/list value (``_a, _b =
    ContextVar(...), ContextVar(...)``), recursively, so each name is paired with the expression
    it actually receives."""
    if isinstance(target, ast.Name):
        return [(target.id, value)]
    if (
        isinstance(target, ast.Tuple | ast.List)
        and isinstance(value, ast.Tuple | ast.List)
        and len(target.elts) == len(value.elts)
    ):
        pairs: list[tuple[str, ast.expr]] = []
        for elt, elt_value in zip(target.elts, value.elts, strict=True):
            pairs.extend(_target_bindings(elt, elt_value))
        return pairs
    return []


def _module_scope_bindings(node: ast.stmt) -> list[tuple[str, ast.expr]]:
    """Every (name, value) pair an assignment statement binds — covering ``name = value``,
    ``name: T = value``, chained ``a = b = value`` and tuple/list destructuring. Empty for a
    bare annotation or any non-assignment statement."""
    if isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.value is not None:
            return [(node.target.id, node.value)]
        return []
    if not isinstance(node, ast.Assign):
        return []
    pairs: list[tuple[str, ast.expr]] = []
    for target in node.targets:
        pairs.extend(_target_bindings(target, node.value))
    return pairs


def _module_scope_statements(body: Sequence[ast.stmt]) -> Iterator[ast.stmt]:
    """Every statement that executes in the module's own namespace, including ones nested in a
    module-level ``if``/``try``/``with``/loop/``match`` — a ``ContextVar`` declared under a
    version check or an optional-import ``try:`` is every bit as module-level as a top-level one,
    and iterating ``tree.body`` alone never sees it."""
    for node in body:
        yield node
        if isinstance(node, ast.If | ast.While | ast.For | ast.AsyncFor):
            yield from _module_scope_statements(node.body)
            yield from _module_scope_statements(node.orelse)
        elif isinstance(node, ast.With | ast.AsyncWith):
            yield from _module_scope_statements(node.body)
        elif isinstance(node, ast.Try | ast.TryStar):
            yield from _module_scope_statements(node.body)
            for handler in node.handlers:
                yield from _module_scope_statements(handler.body)
            yield from _module_scope_statements(node.orelse)
            yield from _module_scope_statements(node.finalbody)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                yield from _module_scope_statements(case.body)


def _contextvar_aliases(tree: ast.Module) -> frozenset[str]:
    """Every local name in *tree* that refers to ``contextvars.ContextVar``."""
    names = {"ContextVar"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "contextvars":
            names.update(
                alias.asname for alias in node.names if alias.name == "ContextVar" and alias.asname
            )
    return frozenset(names)


def _contextvar_names(tree: ast.Module) -> set[str]:
    """Module-scope names bound to a ``ContextVar(...)`` call — bare, qualified or aliased,
    at top level or nested in a module-scope block, single or tuple target."""
    aliases = _contextvar_aliases(tree)
    names: set[str] = set()
    for node in _module_scope_statements(tree.body):
        for name, value in _module_scope_bindings(node):
            if isinstance(value, ast.Call) and _call_target_name(value.func) in aliases:
                names.add(name)
    return names


def _mutable_cache_names(tree: ast.Module) -> set[str]:
    """Module-scope names bound to a dict/list/set literal or mutable-factory call — the same
    construct-1 check the mutable-state guard runs, kept local so this file has no cross-module
    test import (this suite has no ``from tests....`` precedent). Walks the same module-scope
    statements as ``_contextvar_names`` so a cache nested in a module-level block is seen too."""
    names: set[str] = set()
    for node in _module_scope_statements(tree.body):
        for name, value in _module_scope_bindings(node):
            if _is_mutable_binding(value):
                names.add(name)
    return names


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _engine_root() -> Path:
    return _repo_root() / "src" / "squads"


def _reset_target_candidates(
    root: Path, key_root: Path, exemptions: dict[str, frozenset[str]]
) -> dict[str, set[str]]:
    """Every module-level ContextVar (minus *exemptions*), plus every module-level mutable
    cache living in the same file as one, across *root* — the walk this guard's exhaustiveness
    rests on. Reused as-is by the plant tests below against a synthetic tree."""
    candidates: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(key_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        cvars = _contextvar_names(tree) - exemptions.get(rel, frozenset())
        if not cvars:
            continue
        found = set(cvars) | _mutable_cache_names(tree)
        candidates[rel] = found
    return candidates


def _extract_str_frozenset(node: ast.expr) -> frozenset[str]:
    """``frozenset({"a", "b"})`` literal -> ``{"a", "b"}``."""
    assert isinstance(node, ast.Call), node
    assert _call_target_name(node.func) == "frozenset", ast.dump(node)
    (arg,) = node.args
    assert isinstance(arg, ast.Set), ast.dump(arg)
    names: list[str] = []
    for elt in arg.elts:
        assert isinstance(elt, ast.Constant) and isinstance(elt.value, str), ast.dump(elt)
        names.append(elt.value)
    return frozenset(names)


def _read_ambient_reset_targets_from_conftest() -> dict[str, frozenset[str]]:
    """Parse ``tests/conftest.py``'s own ``_AMBIENT_RESET_TARGETS`` literal via ``ast`` (not by
    importing the module — this suite has no cross-test-module import convention and
    ``conftest.py`` carries process-wide import-time side effects better not run twice)."""
    conftest_path = _repo_root() / "tests" / "conftest.py"
    tree = ast.parse(conftest_path.read_text(encoding="utf-8"))
    for node in tree.body:
        for name, value in _module_scope_bindings(node):
            if name != "_AMBIENT_RESET_TARGETS":
                continue
            assert isinstance(value, ast.Dict), ast.dump(value)
            result: dict[str, frozenset[str]] = {}
            for key, val in zip(value.keys, value.values, strict=True):
                assert (
                    key is not None and isinstance(key, ast.Constant) and isinstance(key.value, str)
                ), ast.dump(key) if key is not None else "dict unpacking (**) is not supported"
                result[key.value] = _extract_str_frozenset(val)
            return result
    raise AssertionError("tests/conftest.py has no module-level _AMBIENT_RESET_TARGETS")


# --------------------------------------------------------------------------------- the guard


def test_ambient_reset_targets_are_exhaustive_against_the_source_tree() -> None:
    candidates = _reset_target_candidates(_engine_root(), _repo_root(), CONTEXTVAR_EXEMPTIONS)
    expected = {rel: set(names) for rel, names in RESET_TARGETS.items()}
    assert candidates == expected, (
        "ambient render state outside RequestContext does not match RESET_TARGETS — either a "
        "new leaking value needs a harness reset (add it to tests/conftest.py's "
        "_AMBIENT_RESET_TARGETS and to RESET_TARGETS here), or a ContextVar here needs a "
        f"reasoned CONTEXTVAR_EXEMPTIONS entry: {candidates}"
    )


def test_registered_reset_targets_match_what_conftest_actually_resets() -> None:
    declared_in_conftest = _read_ambient_reset_targets_from_conftest()
    assert declared_in_conftest == RESET_TARGETS, (
        "tests/conftest.py's _AMBIENT_RESET_TARGETS has drifted from this guard's "
        "RESET_TARGETS "
        f"— keep them identical: {declared_in_conftest} != {RESET_TARGETS}"
    )


# ------------------------------------------------------------- wired-guard plant tests
# These exercise the SAME walk (`_reset_target_candidates`) the real assertion above runs, not
# just the bare detector, so a leak reddens the actual guard path automatically.


def test_the_wired_guard_reddens_on_a_planted_bare_contextvar_leak(tmp_path: Path) -> None:
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_leaky_module.py").write_text(
        "from contextvars import ContextVar\n\n"
        '_leak: ContextVar[str | None] = ContextVar("_leak", default=None)\n',
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {"engine/_leaky_module.py": {"_leak"}}


def test_the_wired_guard_pulls_in_a_companion_cache_sharing_the_leaking_contextvars_module(
    tmp_path: Path,
) -> None:
    """A module-level dict beside a leaking ContextVar is flagged as one candidate pair."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_leaky_module.py").write_text(
        "from contextvars import ContextVar\n\n"
        '_leak: ContextVar[str | None] = ContextVar("_leak", default=None)\n\n'
        "_companion_cache: dict = {}\n",
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {"engine/_leaky_module.py": {"_leak", "_companion_cache"}}


def test_an_exempted_contextvar_is_not_flagged_and_its_companion_cache_stays_clear(
    tmp_path: Path,
) -> None:
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_scoped_module.py").write_text(
        "from contextvars import ContextVar\n\n"
        '_scoped: ContextVar[str | None] = ContextVar("_scoped", default=None)\n\n'
        "_unrelated_cache: dict = {}\n",
        encoding="utf-8",
    )
    custom_exemptions = {"engine/_scoped_module.py": frozenset({"_scoped"})}

    candidates = _reset_target_candidates(planted_root, tmp_path, custom_exemptions)

    assert candidates == {}


def test_a_module_with_a_mutable_cache_and_no_contextvar_is_never_a_candidate(
    tmp_path: Path,
) -> None:
    """A module-level cache is only a candidate when it shares a file with a leaking ContextVar."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_plain_cache_module.py").write_text("_cache: dict = {}\n", encoding="utf-8")

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {}


def test_the_wired_guard_reddens_on_a_contextvar_imported_under_an_alias(tmp_path: Path) -> None:
    """`from contextvars import ContextVar as CV` then `_leak = CV(...)`."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_aliased_module.py").write_text(
        "from contextvars import ContextVar as CV\n\n"
        '_leak: CV[str | None] = CV("_leak", default=None)\n',
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {"engine/_aliased_module.py": {"_leak"}}


def test_the_wired_guard_reddens_on_a_contextvar_declared_inside_a_module_level_try(
    tmp_path: Path,
) -> None:
    """An optional-import `try:` at module level still binds in the module's own namespace."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_try_nested_module.py").write_text(
        "from contextvars import ContextVar\n\n"
        "try:\n"
        '    _leak: ContextVar[str | None] = ContextVar("_leak", default=None)\n'
        "except ImportError:  # pragma: no cover\n"
        "    _leak = None\n",
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {"engine/_try_nested_module.py": {"_leak"}}


def test_the_wired_guard_reddens_on_a_contextvar_declared_inside_a_module_level_if(
    tmp_path: Path,
) -> None:
    """Same nesting, under a version/platform check — including from the `else` branch."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_if_nested_module.py").write_text(
        "import sys\n"
        "from contextvars import ContextVar\n\n"
        "if sys.version_info >= (3, 14):\n"
        '    _leak: ContextVar[str | None] = ContextVar("_leak", default=None)\n'
        "else:  # pragma: no cover\n"
        '    _fallback_leak: ContextVar[str | None] = ContextVar("_fallback", default=None)\n',
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {"engine/_if_nested_module.py": {"_leak", "_fallback_leak"}}


def test_the_wired_guard_reddens_on_contextvars_bound_by_a_tuple_target(tmp_path: Path) -> None:
    """`_a, _b = ContextVar(...), ContextVar(...)` binds two ambient values in one statement."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_tuple_target_module.py").write_text(
        "from contextvars import ContextVar\n\n"
        '_a, _b = ContextVar("_a", default=None), ContextVar("_b", default=None)\n'
        '_c, _not_a_leak = ContextVar("_c", default=None), "plain"\n',
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {"engine/_tuple_target_module.py": {"_a", "_b", "_c"}}


def test_a_contextvar_bound_in_a_function_or_class_body_is_not_module_level(
    tmp_path: Path,
) -> None:
    """The boundary the nesting widening deliberately stops at, pinned."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_inner_scope_module.py").write_text(
        "from contextvars import ContextVar\n\n"
        "def _make() -> None:\n"
        '    _local = ContextVar("_local", default=None)\n\n'
        "class _Holder:\n"
        '    _attr = ContextVar("_attr", default=None)\n',
        encoding="utf-8",
    )

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {}
