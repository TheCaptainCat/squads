"""A migration runner is frozen against the live tree it runs under — it may carry its own frozen
literals, but it may never import an on-disk *wire-encoding* primitive from ``_models``: a name
whose value or return shape is how an id/ref/padding literal gets written to a file."""

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
        "normalise_ref_kinds",
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
    """True if the module imports ``squads`` at all — ``import squads``, ``import squads.anything``
    (aliased or not), ``from squads import anything``, ``from squads.anything import anything`` —
    not narrowed to ``_models``."""
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
        "from squads._models._item import normalise_ref_kinds\n\n"
        "def use():\n    return normalise_ref_kinds([], default_kind='related')\n",
        encoding="utf-8",
    )

    hits = _scan(tmp_path)
    assert hits == [("src/squads/_migrations/_example.py", "normalise_ref_kinds")]


def test_the_scan_catches_the_purely_mechanical_ref_primitives_too(tmp_path: Path) -> None:
    """``split_ref``/``make_ref`` are no longer exempt."""
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
    """The rule reaches constants."""
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
    """A model/schema definition that encodes no wire literal of its own — ``Item``."""
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
    """The evasion a direct ``from ... import <name>`` scan misses: import the module."""
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
    """Same evasion, without the ``as`` — the alias is not what made the earlier shape invisible."""
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
    """Importing the `_models` package by name, then a longer attribute chain, is caught."""
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
    """Importing `squads._models` alone is not a hit; naming a forbidden attribute is."""
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
    """The widened evasion: a bare ``import squads``."""
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
    """A bare `import squads` used only to reach a schema definition is not flagged."""
    planted = tmp_path / "src" / "squads" / "_migrations" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import squads\n\n"
        "def use():\n    return squads._models._item.Item, squads._models._subentity.SubEntity\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []


def test_wire_encoding_primitives_are_pinned_to_models_item() -> None:
    """Every name this guard forbids must resolve in ``squads._models._item`` today."""
    missing = sorted(n for n in _WIRE_ENCODING_PRIMITIVES if not hasattr(models_item, n))
    assert not missing, (
        "_WIRE_ENCODING_PRIMITIVES names a primitive that no longer resolves in "
        f"squads._models._item -- the guard is silently protecting nothing for it, update the "
        f"set (or restore the name): {missing}"
    )
