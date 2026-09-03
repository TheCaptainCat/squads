"""A migration runner is frozen against the live tree it runs under — it may carry its own
frozen literals, but it may never import an on-disk *wire-encoding* primitive from ``_models``:
a name whose value or return shape is how an id/ref/padding literal gets written to a file.

The rule used to be framed the other way round: "does this primitive resolve *vocabulary*" —
and ``split_ref``/``make_ref`` were pinned as permanently exempt on the ground that they were
"structural — no vocabulary of their own". That framing is what let the defect back in. Once
``make_ref`` genuinely became structural (no baked-in default-kind collapse), a frozen runner
that still imported it started writing different bytes for the same input than it always had —
the collapse decision the runner's *own* on-disk output depends on had moved out from under the
import without the import itself changing shape at all. "Structural today" was never a
permanent property the guard could verify by name; a future refactor can always move a
live-tree decision back underneath a name that currently looks purely mechanical, and type
checking cannot catch it — the signature stays compatible either way.

The rule this guard now enforces asks a different question, one that does not depend on
inspecting today's implementation: **can anything in the live tree change what this name makes
a frozen runner write, without the runner's own source changing?** For a wire-encoding
primitive the answer is always "maybe, later" — not because it currently does, but because
nothing prevents a future edit from making it so, and the runner has no way to notice. So the
answer does not turn on today's purity; it turns on *category*. Every name that formats,
parses, or supplies a width/default for an id or ref literal is forbidden, unconditionally,
with no per-name exemption — ``make_ref``, ``split_ref`` and ``fold_legacy_kinds`` included.
A migration that needs one carries a private, frozen copy instead (see
``_v0_1_to_v0_2._split_ref``/``_make_ref`` and ``_v0_5_to_v0_7._split_ref``/``_make_ref``/
``_format_item_id``).

The rule reaches constants as well as functions, for the same reason:
:data:`squads._models._item.DISPLAY_ID_PADDING` is a bare value, not a decision, but it *is*
the width the 0.5-to-0.7 runner's frozen ``_unpad_ref`` writes — a live change to that constant
would move the runner's bytes exactly the way the ``make_ref`` collapse did. It is judged under
this rule and forbidden the same as the functions; the runner freezes its own copy
(``_v0_5_to_v0_7._DISPLAY_ID_PADDING``).

``format_item_id`` is judged too, and forbidden for the same reason, not exempted as
"obviously fine because it only formats its own arguments": a wire-encoding primitive's
*current* implementation being a pure function of its arguments is exactly the property that
was true of ``make_ref`` right up until the collapse decision moved inside it, so "looks pure
today" cannot be the test a permanent exemption rests on. Both runners that need it freeze
their own ``_format_item_id`` instead.

What stays importable: model/schema *definitions* that carry no wire-encoding decision of
their own — ``Item``, ``SubEntity``, ``ExtraKey``, the ``_markers`` section-tag constants. A
migration reads and writes the *shape* of those on every schema version; freezing them would
mean re-deriving pydantic's own field set by hand for no safety gained, since none of them
format or collapse anything.

What the scan actually walks: a direct ``from squads._models... import <name>`` naming a
forbidden primitive is always a hit, aliased or not. A module-level import that merely *reaches*
into ``squads`` at all — ``import squads`` down to ``import squads._models._item`` (aliased or
not), or ``from squads import ...`` at any depth — is not itself a hit; it only becomes one if
the same file also carries an attribute access whose attribute name is a forbidden primitive
(``_item.make_ref``, ``squads._models._item.split_ref``, ...), anywhere in the file. The trigger
is deliberately not narrowed to an import that names ``_models`` in the statement itself, because
a fully-dotted chain off a bare ``import squads`` reaches the same primitive without ever naming
``_models`` in an import. A module import that never names a forbidden attribute stays unflagged,
so a plain ``Item``/``SubEntity``/``ExtraKey``/``markers`` import — reached however — is left
alone. This is a name-shape scan, not a data-flow one: it does not prove the attribute resolves
back to the reached import, only that both are present in the same file, which is the deliberate
over-approximation for a guard on the integrity core.

What it cannot walk: dynamic dispatch. ``getattr(module, "make_ref")`` (or a name built from a
string at runtime) never produces an ``ast.Attribute`` node, so no static AST scan — this one
included — can see it. That is a limit of the mechanism, not a gap left uncovered by omission;
closing it would need a different technique (import-time monkeypatching of the target names, or
a runtime audit hook), not a wider AST rule. The guard's actual guarantee is: every *statically
named* reach for a forbidden primitive, however the reimport is phrased, is caught.

Two runners hold this today. ``_v0_1_to_v0_2.py`` used to import ``fold_legacy_kinds`` before
it became live-spec-aware; the runner now carries its own frozen copy
(``_v0_1_to_v0_2._fold_legacy_kinds``). ``_v0_5_to_v0_7.py`` used to import ``split_ref``,
``make_ref``, ``format_item_id`` and ``DISPLAY_ID_PADDING``; it now carries frozen copies of
all four.

This guard does not merge with the separate scan that flags a hardcoded ref-kind literal
outside the spec layer — that scan excludes ``_migrations/`` by construction, since a migration
legitimately reads the vocabulary of the schema version it transforms as a frozen local
literal. This guard covers the complementary axis: never reaching into the *live* tree for the
encoding decision itself. Both must keep passing.
"""

import ast
from pathlib import Path

from squads._models import _item as models_item

#: Names that format, parse, or otherwise supply the on-disk encoding of an id/ref/padding
#: literal — "wire-encoding primitives" in the module docstring's terms. Never a name simply
#: because it currently *resolves vocabulary*; a name earns exemption from this set only by
#: never encoding a wire literal at all (a model/schema definition — see the docstring). Extend
#: this set, never narrow the scan to "only functions" or "only names that still resolve
#: vocabulary today" — the whole point is that today's implementation shape is not the test.
_WIRE_ENCODING_PRIMITIVES: frozenset[str] = frozenset(
    {
        "fold_legacy_kinds",
        "make_ref",
        "split_ref",
        "format_item_id",
        "DISPLAY_ID_PADDING",
        "DEFAULT_ID_PADDING",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _reaches_squads(tree: ast.Module) -> bool:
    """True if the module imports ``squads`` at all — ``import squads``, ``import
    squads.anything`` (aliased or not), ``from squads import anything``, ``from squads.anything
    import anything`` — not narrowed to ``_models``. A dotted attribute chain
    (``squads._models._item.make_ref``) can start from any of those roots, so the trigger has to
    arm on reaching the package, not on naming ``_models`` in the import statement itself; naming
    a specific primitive by ``from ... import <name>`` is caught on its own by
    ``_imported_forbidden_names`` below without needing this at all."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name == "squads" or alias.name.startswith("squads.") for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "squads" or module.startswith("squads."):
                return True
    return False


def _imported_forbidden_names(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if not (module == "squads._models" or module.startswith("squads._models.")):
            continue
        found.update(alias.name for alias in node.names if alias.name in _WIRE_ENCODING_PRIMITIVES)
    if _reaches_squads(tree):
        # The import reaches into squads by module rather than naming the primitive directly
        # (``import squads._models._item as _item`` / ``from squads import _models`` / a bare
        # ``import squads`` reached via a fully-dotted chain), so the AST alone cannot see which
        # name the primitive was reimported under. Any attribute access naming a forbidden
        # primitive, anywhere in the file, is treated as reaching it through that import — the
        # deliberate over-approximation the module docstring names.
        found.update(
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr in _WIRE_ENCODING_PRIMITIVES
        )
    return found


def _scan(root: Path) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    base = root / "src" / "squads" / "_migrations"
    if not base.is_dir():
        return hits
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        rel = path.relative_to(root).as_posix()
        hits.extend((rel, name) for name in sorted(_imported_forbidden_names(tree)))
    return hits


def test_no_migration_module_imports_a_wire_encoding_primitive_from_models() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}: imports {name!r}" for path, name in hits)
    assert not hits, (
        "a _migrations/ module imports a live wire-encoding primitive from _models -- "
        f"freeze a private copy in the runner instead:\n{detail}"
    )


def test_the_scan_would_catch_a_planted_reimport(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from squads._models._item import fold_legacy_kinds\n\n"
        "def use():\n    return fold_legacy_kinds([], {}, default_kind='related')\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "fold_legacy_kinds")]


def test_the_scan_catches_the_purely_mechanical_ref_primitives_too(tmp_path: Path) -> None:
    """``split_ref``/``make_ref`` are no longer exempt. Being purely mechanical *today* is not
    proof they stay that way — that exact belief is what let ``_v0_5_to_v0_7`` drift when
    ``make_ref``'s default-kind collapse moved elsewhere. A frozen runner carries its own copy
    instead of importing either name, so both are flagged like any other wire-encoding
    primitive."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from squads._models._item import make_ref, split_ref\n\n"
        "def use():\n    return make_ref(*split_ref('X:y'))\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert {name for _, name in hits} == {"make_ref", "split_ref"}


def test_the_scan_catches_a_planted_padding_constant_import(tmp_path: Path) -> None:
    """The rule reaches constants, not only functions: :data:`DISPLAY_ID_PADDING`'s *value* is
    the width a frozen runner writes, so importing it live is caught the same as importing a
    live function would be."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from squads._models._item import DISPLAY_ID_PADDING\n\n"
        "def use():\n    return DISPLAY_ID_PADDING\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "DISPLAY_ID_PADDING")]


def test_the_scan_leaves_schema_definitions_importable(tmp_path: Path) -> None:
    """A model/schema definition that encodes no wire literal of its own — ``Item``,
    ``SubEntity``, the ``_markers`` section-tag constants — stays importable. This guard scans
    for the named wire-encoding primitives, never for "any ``_models`` import"."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from squads._models._item import Item\n"
        "from squads._models._subentity import SubEntity\n"
        "from squads._models import _markers as markers\n\n"
        "def use():\n    return Item, SubEntity, markers\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []


def test_the_scan_catches_a_module_import_plus_attribute_access(tmp_path: Path) -> None:
    """The evasion a direct ``from ... import <name>`` scan misses: import the module and reach
    the primitive through attribute access instead of naming it in the import statement."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import squads._models._item as _item\n\n"
        "def use():\n    return _item.make_ref('X', 'related')\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "make_ref")]


def test_the_scan_catches_an_unaliased_module_import_plus_attribute_access(
    tmp_path: Path,
) -> None:
    """Same evasion, without the ``as`` — the alias is not what made the earlier shape
    invisible, the missing ``ast.Import`` handling was."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import squads._models._item\n\n"
        "def use():\n    return squads._models._item.split_ref('X:y')\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "split_ref")]


def test_the_scan_catches_a_package_import_plus_attribute_chain(tmp_path: Path) -> None:
    """The second evasion shape: import the ``_models`` package by name rather than a specific
    submodule, then reach the primitive through a longer attribute chain."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from squads import _models\n\n"
        "def use():\n    return _models._item.make_ref('X', 'related')\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "make_ref")]


def test_a_models_module_import_naming_no_forbidden_attribute_stays_unflagged(
    tmp_path: Path,
) -> None:
    """The no-false-positive leg: reaching into ``squads._models`` by module import is not
    itself a hit — only doing so *and* naming a forbidden attribute is. A future author must not
    be pushed toward suppressing the guard because a legitimate schema-definition import (via
    module form rather than ``from ... import Item``) got flagged for nothing it does."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import squads._models._item as _item\n"
        "from squads import _models\n\n"
        "def use():\n    return _item.Item, _models._subentity.SubEntity\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []


def test_the_scan_catches_a_bare_squads_import_plus_fully_dotted_attribute_chain(
    tmp_path: Path,
) -> None:
    """The widened evasion: a bare ``import squads`` (naming nothing under ``_models`` in the
    import statement at all) reaches the same primitive through a fully-dotted attribute chain.
    Narrowing the trigger to imports that name ``_models`` specifically left exactly this shape
    open — the same failure mode the guard exists to close, one level up."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import squads\n\ndef use():\n    return squads._models._item.make_ref('X', 'related')\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "make_ref")]


def test_a_bare_squads_import_naming_no_forbidden_attribute_stays_unflagged(
    tmp_path: Path,
) -> None:
    """The no-false-positive leg for the widened trigger: a bare ``import squads`` used only to
    reach a schema definition (never a forbidden attribute) must not be flagged — otherwise the
    broadened rule punishes every ordinary ``import squads...`` in the tree for nothing it
    does."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import squads\n\n"
        "def use():\n    return squads._models._item.Item, squads._models._subentity.SubEntity\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []


def test_wire_encoding_primitives_are_pinned_to_models_item() -> None:
    """Every name this guard forbids must resolve in ``squads._models._item`` today. A miss
    means the name was renamed or moved and the guard is now silently vacuous for it — the set
    has to be updated, not the failure suppressed."""
    missing = sorted(n for n in _WIRE_ENCODING_PRIMITIVES if not hasattr(models_item, n))
    assert not missing, (
        "_WIRE_ENCODING_PRIMITIVES names a primitive that no longer resolves in "
        f"squads._models._item -- the guard is silently protecting nothing for it, update the "
        f"set (or restore the name): {missing}"
    )
