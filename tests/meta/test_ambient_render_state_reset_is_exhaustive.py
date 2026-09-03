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
"""

import ast
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


def _module_scope_target_and_value(node: ast.stmt) -> tuple[str, ast.expr] | None:
    """The (name, value) pair for a simple module-scope ``name = value`` or
    ``name: T = value`` statement, or ``None`` for anything else (tuple targets, bare
    annotations, non-assignments)."""
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return node.targets[0].id, node.value
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    ):
        return node.target.id, node.value
    return None


def _contextvar_names(tree: ast.Module) -> set[str]:
    """Module-scope names bound to a ``ContextVar(...)`` call, bare or qualified."""
    names: set[str] = set()
    for node in tree.body:
        pair = _module_scope_target_and_value(node)
        if pair is None:
            continue
        name, value = pair
        if isinstance(value, ast.Call) and _call_target_name(value.func) == "ContextVar":
            names.add(name)
    return names


def _mutable_cache_names(tree: ast.Module) -> set[str]:
    """Module-scope names bound to a dict/list/set literal or mutable-factory call — the same
    construct-1 check the mutable-state guard runs, kept local so this file has no cross-module
    test import (this suite has no ``from tests....`` precedent)."""
    names: set[str] = set()
    for node in tree.body:
        pair = _module_scope_target_and_value(node)
        if pair is None:
            continue
        name, value = pair
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
        pair = _module_scope_target_and_value(node)
        if pair is None or pair[0] != "_AMBIENT_RESET_TARGETS":
            continue
        value = pair[1]
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
    allowlists on its own terms, e.g. a loaded-once catalog) is out of scope for this guard."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_plain_cache_module.py").write_text("_cache: dict = {}\n", encoding="utf-8")

    candidates = _reset_target_candidates(planted_root, tmp_path, CONTEXTVAR_EXEMPTIONS)

    assert candidates == {}
