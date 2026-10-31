"""Repo-hygiene gate: a stored badge value is read through ``badge_value``, never through
``getattr(entity, field.code)``."""

import ast
from datetime import UTC, datetime
from pathlib import Path

from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._workflow import bundled_spec
from tests.meta import _vocabulary as vocabulary
from tests.meta._roots import REPO_ROOT


def _reads_by_field_code(source: str) -> list[int]:
    """The lines of *source* that call ``getattr`` with an expression ending in ``.code`` as the
    attribute name: a dynamic read keyed by a declared code."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Attribute)
        and node.args[1].attr == "code"
    ]


def _hits(root: Path) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for path in vocabulary.source_files(root, ".py"):
        lines = _reads_by_field_code(path.read_text(encoding="utf-8"))
        if lines:
            found[path.relative_to(root).as_posix()] = lines
    return found


def test_no_source_file_reads_a_badge_value_by_getattr_on_its_field_code() -> None:
    hits = _hits(REPO_ROOT)
    assert not hits, (
        "a stored badge value is read with getattr(obj, <field>.code), which skips every "
        "declared field without a same-named model attribute. Use "
        f"obj.badge_value(<field>.code) instead: {hits}"
    )


def test_the_scan_sees_the_shape_it_forbids_and_not_the_accessor(tmp_path: Path) -> None:
    root = tmp_path / "src" / "squads"
    root.mkdir(parents=True)
    (root / "_a.py").write_text("code = getattr(obj, f.code, None)\n", encoding="utf-8")
    (root / "_b.py").write_text(
        "code = obj.badge_value(f.code)\nx = getattr(ctx, name)\n", encoding="utf-8"
    )

    assert _hits(tmp_path) == {"src/squads/_a.py": [1]}


def test_items_and_sub_entities_store_a_declared_badge_value_under_its_code() -> None:
    spec = bundled_spec()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    type_name = next(t for t in spec.items if spec.fields_for(t))
    code = spec.fields_for(type_name)[0].code
    item = Item(
        sequence_id=1,
        type=type_name,
        title="t",
        slug="t",
        status=spec.initial_status(type_name),
        path="x.md",
        created_at=now,
        updated_at=now,
    )
    item.set_badge_value(code, "kept")
    assert item.badge_value(code) == "kept"

    kind = next(k for k in spec.subentity_kinds if spec.fields_for(k))
    kind_code = spec.fields_for(kind)[0].code
    sub = SubEntity(local_id="X1", title="s", status=spec.subentity_initial(kind))
    sub.set_badge_value(kind_code, "kept")
    assert sub.badge_value(kind_code) == "kept"
