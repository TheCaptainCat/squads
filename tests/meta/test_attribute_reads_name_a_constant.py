"""Repo-hygiene gate: no reader indexes the item's attribute mapping by a string literal.

Internals read an attribute through an ``AttributeKey`` constant and the item accessor, so a key
is spelled once. A table of the read shapes the scan must catch, a clean tree, and the planted
read that proves the scan has reach.
"""

import ast
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src" / "squads"


def _is_attributes(node: ast.expr) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "attributes"


def _is_literal(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def literal_attribute_reads(source: str) -> list[int]:
    """The line of every read or write of the attribute mapping, or of ``item.attribute(...)``,
    whose key is a string literal."""
    hits: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Subscript)
            and _is_attributes(node.value)
            and _is_literal(node.slice)
        ):
            hits.append(node.lineno)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            on_mapping = _is_attributes(node.func.value) and node.func.attr in {
                "get",
                "pop",
                "setdefault",
            }
            is_accessor = node.func.attr == "attribute"
            if (on_mapping or is_accessor) and node.args and _is_literal(node.args[0]):
                hits.append(node.lineno)
        elif (
            isinstance(node, ast.Compare)
            and any(_is_attributes(c) for c in node.comparators)
            and _is_literal(node.left)
            and any(isinstance(op, ast.In | ast.NotIn) for op in node.ops)
        ):
            hits.append(node.lineno)
    return sorted(hits)


#: (id, source): each is a literal-keyed read the scan must report.
PLANTED = [
    ("subscript", "item.attributes['tech']"),
    ("get", "item.attributes.get('tech')"),
    ("pop", "item.attributes.pop('tech', None)"),
    ("setdefault", "item.attributes.setdefault('tech', 'x')"),
    ("accessor", "item.attribute('tech')"),
    ("membership", "'tech' in item.attributes"),
    ("assignment", "item.attributes['tech'] = 'x'"),
]

#: (id, source): reads through a constant or a variable, which are not literals.
ALLOWED = [
    ("constant", "item.attributes[AttributeKey.TECH]"),
    ("variable", "item.attributes.get(key)"),
    ("accessor-constant", "item.attribute(AttributeKey.TECH)"),
]


@pytest.mark.parametrize("source", [s for _, s in PLANTED], ids=[i for i, _ in PLANTED])
def test_the_scan_reports_a_literal_keyed_read(source: str) -> None:
    assert literal_attribute_reads(source) == [1]


@pytest.mark.parametrize("source", [s for _, s in ALLOWED], ids=[i for i, _ in ALLOWED])
def test_the_scan_leaves_a_constant_keyed_read_alone(source: str) -> None:
    assert literal_attribute_reads(source) == []


def test_no_reader_in_the_source_tree_indexes_attributes_by_a_literal() -> None:
    found = {
        f"{path.relative_to(_SRC)}:{line}": None
        for path in sorted(_SRC.rglob("*.py"))
        for line in literal_attribute_reads(path.read_text(encoding="utf-8"))
    }
    assert not found, f"name the key with an AttributeKey constant: {sorted(found)}"
