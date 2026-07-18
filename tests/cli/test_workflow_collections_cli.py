"""``sq workflow collections`` — the badge-collection-vocabulary machine surface.

Default prints a human Rich table; ``--json`` emits the frozen bare-array shape
(``{collection, label, ordered, default, badges: [{code, label, emoji}]}``), ascending
collection code. The byte-identical golden is pinned in ``tests/cli/test_json_output_shape.py``
(``tests/goldens/workflow_collections.json``) — this module covers the field-set/model
contract and the human table.
"""

import json

import pytest

from squads._cli._workflow_cmd import (
    COLLECTION_BADGE_ENTRY_FIELDS,
    COLLECTION_CATALOG_FIELDS,
    _collection_catalog,  # pyright: ignore[reportPrivateUsage]
)
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


# ─── CLI surface ────────────────────────────────────────────────────────────────


async def test_default_output_is_a_human_table_with_every_declared_collection(
    project, invoke
) -> None:
    result = await invoke(["workflow", "collections"])
    assert result.exit_code == 0
    for col in ("Collection", "Label", "Ordered", "Default", "Badges"):
        assert col in result.output
    for coll in ("priority", "severity"):
        assert coll in result.output


async def test_json_emits_a_bare_array_of_every_declared_collection_in_ascending_order(
    project, invoke
) -> None:
    result = await invoke(["workflow", "collections", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    codes = [r["collection"] for r in rows]
    assert codes == sorted(codes)
    assert set(codes) >= {"priority", "severity"}


async def test_json_badges_are_codes_never_rendered_glyphs(project, invoke) -> None:
    """Items emit codes; the catalog is where glyph/label live."""
    result = await invoke(["workflow", "collections", "--json"])
    rows = {r["collection"]: r for r in json.loads(result.output)}
    priority_codes = [b["code"] for b in rows["priority"]["badges"]]
    assert priority_codes == ["urgent", "high", "medium", "low"]
    urgent = next(b for b in rows["priority"]["badges"] if b["code"] == "urgent")
    assert urgent["label"] == "Urgent"
    assert urgent["emoji"] == "🔴"


async def test_json_ordered_and_default_match_the_spec(project, invoke) -> None:
    result = await invoke(["workflow", "collections", "--json"])
    rows = {r["collection"]: r for r in json.loads(result.output)}
    spec = load_workflow_spec()
    for code, coll in spec.collections.items():
        assert rows[code]["ordered"] == coll.ordered
        assert rows[code]["default"] == coll.default
        assert rows[code]["label"] == coll.label


# ─── field-set / model contract ─────────────────────────────────────────────────


def test_frozen_field_set_is_exactly_collection_label_ordered_default_badges() -> None:
    assert COLLECTION_CATALOG_FIELDS == ("collection", "label", "ordered", "default", "badges")


def test_frozen_badge_entry_field_set_is_exactly_code_label_emoji() -> None:
    assert COLLECTION_BADGE_ENTRY_FIELDS == ("code", "label", "emoji")


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _collection_catalog(spec):
        assert set(row.keys()) == set(COLLECTION_CATALOG_FIELDS)


def test_every_badge_entry_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _collection_catalog(spec):
        for badge in row["badges"]:  # type: ignore[union-attr]
            assert set(badge.keys()) == set(COLLECTION_BADGE_ENTRY_FIELDS)  # type: ignore[union-attr]


def test_label_ordered_default_badges_are_read_verbatim_off_the_collection_model() -> None:
    spec = load_workflow_spec()
    coll = spec.collections["severity"]
    row = next(r for r in _collection_catalog(spec) if r["collection"] == "severity")
    assert row["label"] == coll.label
    assert row["ordered"] == coll.ordered
    assert row["default"] == coll.default
    assert [b["code"] for b in row["badges"]] == [b.code for b in coll.badges]  # type: ignore[union-attr]
