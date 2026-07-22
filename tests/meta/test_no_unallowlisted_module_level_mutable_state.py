"""Durable enforcement for the engine's static-state precondition — the lasting output of the
statelessness work is a guard, not a one-time sweep.

**Triage rule** (see ``squads._context``'s module docstring for the full statement this
mirrors): a module-level binding is either

- **DATA** — its value varies per request/squad/test — it must live on the single
  ``RequestContext`` object (one dataclass instance in one ``ContextVar``, never a per-field
  ``ContextVar`` and never a bare module global), or
- **CODE/definition** — an immutable spec/class/lookup-table loaded once and safe to share
  across every request — it may stay module-level, allowlisted below.

This test walks every module under ``src/squads`` with :mod:`ast` and flags two constructs at
**module scope** (``ClassVar``s and function-local bindings are out of band by construction —
only a module's own top-level statements are walked):

1. an assignment binding a mutable-type value — a ``dict``/``list``/``set`` literal, a
   dict/list/set comprehension, or a call to a known mutable-container factory
   (``dict``/``list``/``set``/``defaultdict``/``OrderedDict``/``Counter``/``deque``, bare or
   qualified as ``module.Factory(...)``) — any of these mutated in place needs no ``global``
   statement, so the factory-call check matters as much as the literal check;
2. a ``global`` statement anywhere in the module (flags the module-level name it mutates, e.g.
   a lazily-populated cache guarded by a "loaded" flag).

Every hit must be on ``ALLOWLIST`` below — the sanctioned CODE-cache/definition catalog,
enumerated exactly and exhaustively so the guard is green on the current tree, not aspirational.
``ALLOWLIST`` also carries a few names the two constructs above don't
actually flag — immutable spec/catalog singletons built via a plain (non-mutable-factory)
function call (``_BUNDLED_SPEC``, ``_spec``, ``_create_spec``, ``_CATALOG``, ``_PLAYBOOK_SPEC``,
``TERMINAL``, …) — included here anyway because they're the same sanctioned-CODE surface named
in the triage audit; the "no stale entry" test below only requires that every allowlisted name
refers to a real module-level binding, not that the mutable-binding check specifically flags it.

Adding a convenient module global later fails the "matches the allowlist exactly" test below
until it's either moved onto ``RequestContext`` or added here with a one-line reason.
"""

import ast
from pathlib import Path

#: module-scope target -> reason, one entry per sanctioned CODE cache/definition. Keyed by the
#: module's path relative to the repo root (posix form).
ALLOWLIST: dict[str, frozenset[str]] = {
    "src/squads/_backends/_registry.py": frozenset(
        {
            "_REGISTRY",  # backend-class registry — classes, instantiated fresh per get_backend()
            "_loaded",  # idempotent-import guard for the registry above
        }
    ),
    "src/squads/_backends/_claude_code/__init__.py": frozenset({"__all__"}),
    "src/squads/_backends/_agents_md/__init__.py": frozenset({"__all__"}),
    "src/squads/_backends/_claude_code/_frontmatter.py": frozenset(
        {"_VALID_MODELS"}  # fixed vocab of valid model names
    ),
    "src/squads/_workflow/__init__.py": frozenset(
        {
            "__all__",
            "_BUNDLED_SPEC",  # immutable bundled default spec, loaded once
            "WORKFLOWS",  # derived from _BUNDLED_SPEC — read-only view, golden-lock surface
            "SUBENTITY_WORKFLOWS",
            "ALLOWED_PARENTS",
            "TERMINAL",
        }
    ),
    "src/squads/_workflow/_models.py": frozenset(
        {"_SIDE_PRIORITY"}  # fixed side-status sort-priority lookup table
    ),
    "src/squads/_rendering/_engine.py": frozenset(
        {"_env_cache"}  # compiled-template cache, per-squad-dir, LRU-bounded
    ),
    "src/squads/_roles/_catalog.py": frozenset(
        {
            "_CATALOG",  # loaded role-catalog singleton
            "_BY_SLUG",  # derived from _CATALOG
            "BUNDLES",  # derived from _CATALOG — named role bundles for `sq init --roles`
        }
    ),
    "src/squads/_roles/_resolver.py": frozenset(
        {"_PREDEFINED_BY_SLUG"}  # derived from the bundled catalog, not _catalog.py itself
    ),
    "src/squads/_interactions/__init__.py": frozenset(
        {
            "_PLAYBOOK_SPEC",  # loaded playbook singleton
            "PLAYBOOK",  # derived from _PLAYBOOK_SPEC
            "SKILL_DESCRIPTIONS",  # fixed bundled-skill description table
            "CREATE_LANES",  # fixed role -> create-lane-types table
        }
    ),
    "src/squads/_cli/_create.py": frozenset(
        {"_create_spec"}  # bundled spec used to statically register `sq create <type>`
    ),
    "src/squads/_cli/_common.py": frozenset(
        {
            "INTENT_COLORS"  # closed intent->rich-colour lookup table — immutable-by-convention
            # CODE constant, shared read-only across requests
        }
    ),
    "src/squads/_cli/__init__.py": frozenset(
        {
            "_spec",  # bundled spec used to statically register the root command tree
            "_STATIC_TYPES",  # derived from _spec — the statically-registered type-name list
        }
    ),
    "src/squads/_overrides/_manifest.py": frozenset(
        {"_manifest_cache"}  # lazily-loaded, immutable-once-populated package-data manifest
    ),
    "src/squads/_models/_metadata.py": frozenset(
        {
            "EXTRA_FIELDS",  # fixed per-type extra-field catalog
            "_GENERIC_FIELDS",  # fixed generic (non-badge) extra-field catalog
        }
    ),
    "src/squads/_services/_retype.py": frozenset(
        {"_BUNDLED_CONTAINER_HEADINGS"}  # fixed bundled sub-entity container heading table
    ),
    "src/squads/_migrations/_registry.py": frozenset(
        {"MIGRATIONS"}  # the ordered migration table — a point-in-time-frozen definition
    ),
    "src/squads/_migrations/_v0_1_to_v0_2.py": frozenset(
        {"_BODY_KIND"}  # frozen pre-0.2 type -> (kind, marker) snapshot, never re-derived live
    ),
    "src/squads/_migrations/_v0_2_to_v0_3.py": frozenset(
        {"_KIND_BY_TYPE"}  # frozen pre-0.3 type -> kind snapshot
    ),
    "src/squads/_migrations/_meta_compat.py": frozenset(
        {"_LOCAL_ID_PREFIX"}  # frozen pre-migration kind -> local-id-prefix snapshot
    ),
    "src/squads/_services/_validators.py": frozenset(
        {
            "CATALOG",  # closed per-item validator catalog — definition-time, empty in Phase A
            "SQUAD_GLOBAL_CATALOG",  # closed squad-global validator registry, same status
            "CATEGORY_BUNDLES",  # fixed category -> default-bundle lookup table
        }
    ),
}

# ---------------------------------------------------------------------------------- the scan

#: Factories that return a mutable container — flagged whether called bare (``defaultdict(...)``)
#: or qualified (``collections.defaultdict(...)``), same as the plain ``dict``/``list``/``set``
#: constructor calls. A module-scope value built from one of these and mutated in place needs no
#: ``global`` statement, so it would otherwise evade both constructs below entirely.
_MUTABLE_FACTORY_NAMES = frozenset(
    {"dict", "list", "set", "defaultdict", "OrderedDict", "Counter", "deque"}
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _call_target_name(func: ast.expr) -> str | None:
    """The called name for a bare call (``f(...)``) or a qualified one (``mod.f(...)``)."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_mutable_binding(value: ast.expr) -> bool:
    """True for a dict/list/set literal, a dict/list/set comprehension, or a call to a known
    mutable-container factory (see ``_MUTABLE_FACTORY_NAMES``) — construct 1 of the guard."""
    if isinstance(value, ast.Dict | ast.List | ast.Set | ast.DictComp | ast.ListComp | ast.SetComp):
        return True
    return isinstance(value, ast.Call) and _call_target_name(value.func) in _MUTABLE_FACTORY_NAMES


def _mutable_state_hits(tree: ast.Module) -> set[str]:
    """Names flagged by construct 1 (module-scope mutable-shaped assignment) or construct 2
    (a ``global`` statement anywhere in the module, however deeply nested)."""
    hits: set[str] = set()
    for node in tree.body:  # module scope ONLY — class/function bodies are never walked here
        if isinstance(node, ast.Assign) and _is_mutable_binding(node.value):
            hits.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and isinstance(node.target, ast.Name)
            and _is_mutable_binding(node.value)
        ):
            hits.add(node.target.id)
    for node in ast.walk(tree):  # `global` can appear inside a nested function, anywhere
        if isinstance(node, ast.Global):
            hits.update(node.names)
    return hits


def _module_scope_names(tree: ast.Module) -> set[str]:
    """Every name bound at module scope by any assignment, mutable-shaped or not — used only to
    confirm an allowlist entry still refers to something real (catches a stale/renamed entry),
    never to decide what construct 1/2 flags."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _engine_root() -> Path:
    return _repo_root() / "src" / "squads"


def _scan_root_for_hits(root: Path, key_root: Path) -> dict[str, set[str]]:
    """Walk every ``.py`` file under *root* and return its mutable-state hits, keyed by path
    relative to *key_root* (posix form) — the exact walk the real guard test below runs, reused
    by the synthetic-tree tests so they exercise the same wiring, not just the bare detector."""
    hits: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = _mutable_state_hits(tree)
        if found:
            hits[path.relative_to(key_root).as_posix()] = found
    return hits


def _missing_against(
    actual: dict[str, set[str]], allowlist: dict[str, frozenset[str]]
) -> dict[str, set[str]]:
    """The set-difference the real guard asserts is empty: every real hit not covered by
    *allowlist*, per file. Shared by the real assertion and the synthetic-tree plant tests."""
    return {
        rel: names - allowlist.get(rel, frozenset())
        for rel, names in actual.items()
        if names - allowlist.get(rel, frozenset())
    }


def test_module_level_mutable_state_matches_the_allowlist_exactly() -> None:
    repo_root = _repo_root()
    actual = _scan_root_for_hits(_engine_root(), repo_root)
    missing = _missing_against(actual, ALLOWLIST)
    assert not missing, (
        "new module-level mutable state outside the allowlist "
        f"(move it onto RequestContext, or allowlist it with a reason): {missing}"
    )


def test_the_allowlist_has_no_stale_entry() -> None:
    repo_root = _repo_root()
    names_by_file: dict[str, set[str]] = {}
    for rel in ALLOWLIST:
        path = repo_root / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names_by_file[rel] = _module_scope_names(tree) | _mutable_state_hits(tree)

    stale = {
        rel: names - names_by_file.get(rel, set())
        for rel, names in ALLOWLIST.items()
        if names - names_by_file.get(rel, set())
    }
    assert not stale, f"allowlist entries with no corresponding module-level binding: {stale}"


# ------------------------------------------------------------- wired-guard plant tests
# These exercise the SAME file-walk (`_scan_root_for_hits`) + allowlist-diff (`_missing_against`)
# the real assertion above runs — not just the bare detector function — against a synthetic
# tree, so a leak reddens the actual guard path automatically, with no manual edit-then-revert.


def test_the_wired_guard_reddens_on_a_planted_dict_literal_leak(tmp_path: Path) -> None:
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_leaky_module.py").write_text(
        "_leak: dict = {}\n\n\ndef _use() -> None:\n    _leak['x'] = 1\n", encoding="utf-8"
    )

    actual = _scan_root_for_hits(planted_root, tmp_path)
    missing = _missing_against(actual, ALLOWLIST)  # the real allowlist — nothing here is on it

    assert missing == {"engine/_leaky_module.py": {"_leak"}}


def test_the_wired_guard_reddens_on_a_planted_defaultdict_factory_leak(tmp_path: Path) -> None:
    """The exact false-negative class flagged in review: a module-scope cache built from a
    non-{dict,list,set}-literal mutable-container factory and mutated in place — no `global`
    statement needed, so only the broadened factory-call check catches it."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_leaky_module.py").write_text(
        "from collections import defaultdict\n\n"
        "_item_cache: dict = defaultdict(dict)\n\n\n"
        "def _use(squad_dir: str) -> None:\n"
        "    _item_cache[squad_dir]['x'] = 1\n",
        encoding="utf-8",
    )

    actual = _scan_root_for_hits(planted_root, tmp_path)
    missing = _missing_against(actual, ALLOWLIST)

    assert missing == {"engine/_leaky_module.py": {"_item_cache"}}


def test_the_wired_guard_reddens_on_a_qualified_ordereddict_factory_leak(tmp_path: Path) -> None:
    """The qualified-call form (`collections.OrderedDict()`, not a bare imported name) is
    caught the same way — the factory-name check looks at the attribute, not the module path."""
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_leaky_module.py").write_text(
        "import collections\n\n_cache = collections.OrderedDict()\n", encoding="utf-8"
    )

    actual = _scan_root_for_hits(planted_root, tmp_path)
    missing = _missing_against(actual, ALLOWLIST)

    assert missing == {"engine/_leaky_module.py": {"_cache"}}


def test_the_wired_guard_stays_green_when_a_synthetic_tree_matches_its_own_allowlist(
    tmp_path: Path,
) -> None:
    planted_root = tmp_path / "engine"
    planted_root.mkdir()
    (planted_root / "_ok_module.py").write_text("_ok: dict = {}\n", encoding="utf-8")

    actual = _scan_root_for_hits(planted_root, tmp_path)
    custom_allowlist = {"engine/_ok_module.py": frozenset({"_ok"})}

    assert _missing_against(actual, custom_allowlist) == {}


def test_a_global_statement_on_an_unallowlisted_name_is_caught(tmp_path: Path) -> None:
    planted = tmp_path / "_example_engine_module.py"
    planted.write_text(
        "_cache = None\n\n\ndef _populate() -> None:\n    global _cache\n    _cache = {}\n",
        encoding="utf-8",
    )

    tree = ast.parse(planted.read_text(encoding="utf-8"))
    hits = _mutable_state_hits(tree)

    assert "_cache" in hits


def test_a_classvar_or_function_local_binding_is_out_of_band() -> None:
    """ClassVar caches (e.g. the CLI's per-process custom-command-lookup caches) and ordinary
    function-local variables are never module-scope bindings, so they're never flagged —
    documented rationale for why they need no allowlist entry, per the guard's own scope."""
    source = (
        "class _Group:\n"
        "    _custom_cmd_cache: dict = {}\n\n\n"
        "def _fn() -> None:\n"
        "    _local: dict = {}\n"
        "    _local['x'] = 1\n"
    )
    tree = ast.parse(source)
    assert _mutable_state_hits(tree) == set()
