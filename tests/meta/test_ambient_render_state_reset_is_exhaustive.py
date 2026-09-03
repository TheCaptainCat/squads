"""Durable enforcement that the CLI test harness resets *every* per-request ambient value a
real process establishes fresh but a fixture can pre-seed as a side effect of its own setup.

**Triage rule** (see ``squads._context``'s module docstring for the full statement): a
module-level binding is either DATA (its value varies per request/squad/test — it belongs on
the single ``RequestContext`` object) or CODE/definition (immutable, safe to share across every
request). ``tests/meta/test_no_unallowlisted_module_level_mutable_state.py`` already enforces
that split at the production-code level. This guard asks a narrower, harness-facing question:
of the values that legitimately stay module-level, which ones are ambient per-request state a
*fresh process* starts unset/empty, so that a fixture which builds a ``Service`` in-process
(``project``/``svc``, via ``service.init``) can silently pre-seed it — the exact shape of the
bug this whole task exists to close (see the bundled `squads` playbook's task/bug records for
the mechanism, not repeated here). ``squads._rendering._engine._env_cache`` is a legitimate,
correctly-allowlisted CODE cache by that first guard's own rule *and* fixture-primed startup
state by this one — the two properties are not mutually exclusive.

The root callback (``squads._cli.__init__.main_callback``) is where a real process establishes
its per-invocation ambient state. It binds one freshly-computed ``RequestContext`` — every
field recomputed from this invocation's inputs, not merged into whatever was ambient — so
anything living on that object is safe by construction (the sole deliberate exception,
``clock_override``, is carried forward on purpose and is what ``frozen_time`` depends on). A
per-request value living *outside* that binding is a candidate this guard must account for.

Two constructs make a module-level binding such a candidate:

1. a module-level ``ContextVar(...)`` declaration — DATA by definition, since a ``ContextVar``
   only exists to vary per task/thread — unless it is exempted below with a reason (``ALLOWLIST``
   the previous guard calls a "reason", this one calls it the same); a ``ContextVar`` set once at
   construction and never restored is exactly the shape that leaks;
2. any module-level mutable cache (dict/list/set literal, or a known mutable-factory call — the
   same check ``test_no_unallowlisted_module_level_mutable_state.py`` runs) living in the *same
   file* as a non-exempt ``ContextVar`` — presumed keyed off that ambient value, as
   ``_env_cache`` is keyed off ``_active_squad_dir``.

Diffed against ``RESET_TARGETS`` below — closed and enumerated to match today's tree exactly
(``{_active_squad_dir, _env_cache}``, both in ``_rendering/_engine.py``) — so a fourth candidate
(or a third module) fails this guard until it is either exempted with a reason or added here
*and* to ``tests/conftest.py``'s own ``_AMBIENT_RESET_TARGETS`` (checked separately below, so the
registry describing the harness and the harness's actual reset code cannot silently drift apart).

What construct 1 actually covers
--------------------------------
The derivation is a syntactic AST match, not type inference, so its reach is worth stating
exactly rather than as "any new ambient value". It is exhaustive over **names bound to a
``ContextVar(...)`` call in the module's own namespace**:

- under any spelling of the class — bare (``ContextVar(...)``), qualified
  (``contextvars.ContextVar(...)``), or renamed on import
  (``from contextvars import ContextVar as CV``);
- at top level *or* nested in a module-scope ``if``/``try``/``with``/loop/``match`` block, in
  any branch or handler — an optional-import ``try:`` or a version check binds in the module
  namespace just the same;
- through a single target, a chained ``a = b = ...``, or a tuple/list destructuring against a
  literal sequence (``_a, _b = ContextVar(...), ContextVar(...)``).

Function-local and class-body bindings are deliberately **outside** it: they are locals and
class attributes, not module-level ambient state, and no harness reset could address them.

Two shapes are outside it, and neither is a bug this guard should imply it catches:

- **factory indirection** — ``_leak = _make_var("_leak")``, where the helper returns a
  ``ContextVar``. The called name is the factory, and deciding that its return type is a
  ``ContextVar`` needs type inference, which an ``ast`` match does not have. Nothing here
  detects this shape; introducing one is a review question, not a guard question.
- **a bare module-level cache in a file with no ``ContextVar``** — excluded by the
  companion-cache rule of construct 2, by the judgment recorded immediately below.

Construct 2's companion-cache rule is a judgment, stated either way
------------------------------------------------------------------
It stays a **companion heuristic**: a cache is a candidate here only when it shares a file with
a non-exempt ``ContextVar``. The rule is a *proxy* for "keyed off ambient state", and the
property it proxies for can hold with no ``ContextVar`` in the same module — a dict keyed by
squad dir in a file that imports the active dir from elsewhere is ambient-keyed and would not be
flagged here. That shape is the closest one to the original leak, so the control for it is named
rather than assumed: ``tests/meta/test_no_unallowlisted_module_level_mutable_state.py`` reddens
on any new module-level mutable binding under ``src/squads`` regardless of what else is in the
file, and forces an ``ALLOWLIST`` entry carrying a written reason before it can go green.

The residual gap, written down rather than papered over: that sibling guard routes the decision
to a human answering **"is this CODE?"** — immutable, safe to share across requests — while the
question that matters *here* is **"is this fixture-primable?"** — does an in-process fixture
populate it as a side effect of its own setup. ``_env_cache`` is the proof the two can both be
true of one binding: it is a correctly-allowlisted CODE cache over there *and* a reset target
over here. So a new bare ambient-keyed cache is never silent, but it can be allowlisted as CODE
by someone who never considered the harness question — a wider construct 2 (any module-level
mutable cache, companion or not) would close that at the cost of making every sanctioned CODE
cache in the tree a candidate needing an exemption here too. That trade was declined; if the
allowlist reasons ever stop being read with this question in mind, revisit it.
"""

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
    "src/squads/_index/_store.py": frozenset(
        {
            # set(...)/reset(token) paired in the same try/finally (IndexStore.transaction()) —
            # never survives past the call that opened it.
            "_active_transaction",
            # Same enter_read_scope()/exit_read_scope() token-pairing discipline.
            "_read_scope",
        }
    ),
}

#: The closed set of ambient values a real `sq` process establishes fresh that
#: tests/conftest.py's `invoke` fixture must reset per-call. Verified two ways below: against a
#: static re-derivation from src/squads (this file must find no more, no less), and against
#: tests/conftest.py's own `_AMBIENT_RESET_TARGETS` (the registry must describe what the harness
#: actually does).
RESET_TARGETS: dict[str, frozenset[str]] = {
    "src/squads/_rendering/_engine.py": frozenset({"_active_squad_dir", "_env_cache"}),
}


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
    """The (name, value) pairs one assignment *target* binds. A bare ``ast.Name`` binds the
    whole value; a tuple/list target destructures elementwise against a tuple/list value
    (``_a, _b = ContextVar(...), ContextVar(...)``), recursively, so each name is paired with
    the expression it actually receives. A destructuring whose right-hand side is not a literal
    sequence of matching length (``_a, _b = _make_pair()``, a starred target) binds nothing
    this walk can attribute, so it yields no pair."""
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
    version check or an optional-import ``try:`` is every bit as module-level as a top-level
    one, and iterating ``tree.body`` alone never sees it.

    Deliberately *not* ``ast.walk``: that descends into function and class bodies too, where a
    binding is a local or a class attribute rather than the module-level ambient state this
    guard is about. ``FunctionDef``/``AsyncFunctionDef``/``ClassDef`` are simply absent from the
    recursion below, so their bodies are yielded as statements but never entered."""
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
    """Every local name in *tree* that refers to ``contextvars.ContextVar``.

    Always includes the plain spelling, which covers both ``ContextVar(...)`` after an ordinary
    ``from contextvars import ContextVar`` and the qualified ``contextvars.ContextVar(...)``
    form (``_call_target_name`` reports an attribute access by its final attribute). Any
    ``as``-renaming of that import adds its local name, so ``from contextvars import ContextVar
    as CV`` makes ``CV(...)`` recognised. Import statements are collected with ``ast.walk``
    rather than the module-scope walk because an import nested inside a function only ever
    *widens* the set of names treated as ``ContextVar`` — it cannot hide a declaration."""
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
        "tests/conftest.py's _AMBIENT_RESET_TARGETS has drifted from this guard's RESET_TARGETS "
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
    """The exact shape `_env_cache` is: a plain module-level dict living beside a leaking
    ContextVar, keyed off it — flagged as one candidate pair, not just the ContextVar alone."""
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
    """A module-level cache is only a candidate when it shares a file with a leaking
    ContextVar — an ordinary CODE cache (the common case the mutable-state guard already
    allowlists on its own terms, e.g. a loaded-once catalog) is out of scope for this guard.

    This pins the companion-cache judgment, not an oversight: a bare ambient-keyed cache in a
    file with no ContextVar is not detected here, and the control for it is
    test_no_unallowlisted_module_level_mutable_state.py, which reddens on any new module-level
    mutable binding under src/squads. See this module's docstring for the residual gap that
    leaves — that control asks "is this CODE?", not "is this fixture-primable?"."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_plain_cache_module.py").write_text("_cache: dict = {}\n", encoding="utf-8")

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {}


def test_the_wired_guard_reddens_on_a_contextvar_imported_under_an_alias(tmp_path: Path) -> None:
    """`from contextvars import ContextVar as CV` then `_leak = CV(...)`. The candidate test
    matches the *called* name, so without alias resolution any renaming of the import defeats
    it — the leak is identical, only its spelling differs."""
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
    """An optional-import `try:` at module level still binds in the module's own namespace, so
    the value is ambient exactly as a top-level one is — but it lives in the `try` statement's
    own body, which a `tree.body`-only walk never enters."""
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
    """Same nesting, under a version/platform check — including from the `else` branch, so the
    walk cannot be satisfied by descending into `body` alone."""
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
    """`_a, _b = ContextVar(...), ContextVar(...)` binds two ambient values in one statement.
    A target extractor that accepts only a single `ast.Name` returns nothing for it, so both
    leak; destructuring elementwise pairs each name with the call it actually receives — note
    `_not_a_leak`, which must stay out of the result."""
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
    """The boundary the nesting widening deliberately stops at, pinned so a later switch to a
    bare `ast.walk` reddens here: a function-local binding and a class attribute are not the
    module-level ambient state this guard accounts for, and flagging them would report names
    that no harness reset could reach."""
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
