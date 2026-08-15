"""``sq workflow subentity-kinds`` — the sub-entity-kind catalog machine surface.

Default prints a human Rich table; ``--json`` emits the frozen bare-array shape
(``{subentity_kind, lifecycle, plural, local_prefix, container_heading, completion,
maps_parent_story, fields}``) ascending kind name. It is the fifth member of the
``sq workflow`` catalog family and follows the family's row grammar: one row per declared
entry in a documented order, a module-level frozen field-set tuple, every key present on every
row, and references carried by NAME (the type catalog's ``subentity_kind`` joins this
catalog's identity key of the same name).

``fields`` reuses the type row's entry shape verbatim — one ``FIELD_ENTRY_FIELDS`` tuple and
one builder, not a parallel pair — because the sub-entity field mechanism is the item one
unforked and the published shape is part of that. ``placeholder`` is deliberately unpublished:
scaffold prose is content the engine writes into a file, not vocabulary a client resolves.

The byte-identical golden is pinned in ``tests/cli/test_json_output_shape.py``
(``tests/goldens/workflow_subentity_kinds.json``); this module covers the field-set/model
contract, the joins, and a squad that renames, re-prefixes and drops declared vocabulary — a
catalog that is only right for the bundled spec is the exact defect it exists to remove.
"""

import json
from pathlib import Path

import pytest

from squads import __version__
from squads._cli._workflow_cmd import (
    FIELD_ENTRY_FIELDS,
    SUBENTITY_KIND_CATALOG_FIELDS,
    _field_entries,
    _subentity_kind_catalog,
    _type_catalog,
)
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec
from squads._workflow._models import SubentityKindSpec

pytestmark = pytest.mark.anyio

#: A squad that renames a kind, re-prefixes its local ids, rebinds its field to a new
#: collection, moves its completion target, drops a bundled kind's field, and adds a wholly
#: custom kind on a custom type.
_CUSTOMIZED = """\
[collections.impact]
label = "Impact"
ordered = true
default = "cosmetic"
badges = [
  { code = "blocker", label = "Blocker" },
  { code = "cosmetic", label = "Cosmetic" },
]

[statuses.Noted]
role = "pending"
[statuses.Actioned]
role = "done"

[lifecycles.action]
initial = "Noted"
[lifecycles.action.transitions]
Noted = ["Actioned"]

[subentity_kinds.observation]
lifecycle = "finding"
completion = "WontFix"
plural = "observations"
local_prefix = "OB"
placeholder = "_Describe it._"
fields = [
  { code = "impact", label = "Blast radius", collection = "impact", required = true },
]

[subentity_kinds.action]
lifecycle = "action"
completion = "Actioned"
plural = "actions"
local_prefix = "AC"
maps_parent_story = true

[subentity_kinds.story]
plural = "epics_stories"

[items.review]
subentity_kind = "observation"

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
order = 75
subentity_kind = "action"

[selected]
subentity_kinds = ["observation", "action", "story", "subtask"]
"""


def _write_override(squad_dir: Path, body: str) -> None:
    """Write the override, then *prove it loads*.

    The CLI's spec resolution is fail-soft by design: an override it cannot parse or validate
    degrades silently to the bundled spec. A probe whose setup failed that way would keep
    asserting happily against bundled vocabulary — a malformed multi-line TOML inline table
    did exactly that here once. Loading it eagerly turns a broken fixture into a setup error
    rather than a misleading pass.
    """
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)
    load_workflow_spec(squad_dir=squad_dir)


# ─── CLI surface ────────────────────────────────────────────────────────────────


async def test_default_output_is_a_human_table_with_every_declared_kind(project, invoke) -> None:
    result = await invoke(["workflow", "subentity-kinds"])
    assert result.exit_code == 0, result.output
    for col in ("Kind", "Lifecycle", "Plural", "Prefix", "Heading", "Completion", "Fields"):
        assert col in result.output
    for kind in ("finding", "story", "subtask"):
        assert kind in result.output


async def test_json_emits_a_bare_array_ascending_kind_name(project, invoke) -> None:
    result = await invoke(["workflow", "subentity-kinds", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    kinds = [r["subentity_kind"] for r in rows]
    assert kinds == ["finding", "story", "subtask"]
    assert kinds == sorted(kinds)


async def test_json_matches_the_spec_declarations_key_for_key(project, invoke) -> None:
    result = await invoke(["workflow", "subentity-kinds", "--json"])
    rows = {r["subentity_kind"]: r for r in json.loads(result.output)}
    spec = load_workflow_spec()
    for kind, ks in spec.subentity_kinds.items():
        row = rows[kind]
        assert row["lifecycle"] == ks.lifecycle
        assert row["plural"] == ks.plural
        assert row["local_prefix"] == ks.local_prefix
        assert row["completion"] == ks.completion
        assert row["maps_parent_story"] == ks.maps_parent_story
        assert row["container_heading"] == spec.subentity_container_heading(kind)


async def test_json_publishes_no_placeholder(project, invoke) -> None:
    """Scaffold prose is content, not vocabulary — and every bundled kind declares one, so an
    accidental leak would be visible here."""
    result = await invoke(["workflow", "subentity-kinds", "--json"])
    for row in json.loads(result.output):
        assert "placeholder" not in row


# ─── field-set / model contract ─────────────────────────────────────────────────


def test_frozen_field_set_is_exactly_the_eight_declared_keys() -> None:
    assert SUBENTITY_KIND_CATALOG_FIELDS == (
        "subentity_kind",
        "lifecycle",
        "plural",
        "local_prefix",
        "container_heading",
        "completion",
        "maps_parent_story",
        "fields",
    )


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _subentity_kind_catalog(spec):
        assert set(row.keys()) == set(SUBENTITY_KIND_CATALOG_FIELDS)


def test_every_field_entry_has_exactly_the_shared_frozen_entry_set() -> None:
    spec = load_workflow_spec()
    for kind in spec.subentity_kinds:
        for entry in _field_entries(kind, spec):
            assert set(entry.keys()) == set(FIELD_ENTRY_FIELDS)


def test_the_kind_rows_fields_are_the_same_shape_the_type_rows_carry() -> None:
    """One entry tuple and one builder, not a parallel pair — the sub-entity field mechanism
    is the item one unforked, and the published shape is part of that requirement."""
    spec = load_workflow_spec()
    kind_entry = next(r for r in _subentity_kind_catalog(spec) if r["subentity_kind"] == "finding")
    type_entry = next(r for r in _type_catalog(spec) if r["type"] == "bug")
    kind_keys = {frozenset(entry) for entry in kind_entry["fields"]}  # type: ignore[union-attr]
    type_keys = {frozenset(entry) for entry in type_entry["fields"]}  # type: ignore[union-attr]
    assert kind_keys == type_keys == {frozenset(FIELD_ENTRY_FIELDS)}


def test_every_published_key_traces_back_to_the_model() -> None:
    """Five keys are read verbatim off ``SubentityKindSpec``; ``container_heading`` is the
    engine's own resolution (a special-case table, else title-cased plural) and ``fields`` is
    the shared entry builder — guards against a stray key with nothing behind it."""
    for name in ("lifecycle", "plural", "local_prefix", "completion", "maps_parent_story"):
        assert name in SubentityKindSpec.model_fields
    assert "fields" in SubentityKindSpec.model_fields
    assert "placeholder" in SubentityKindSpec.model_fields  # declared, deliberately unpublished


def test_container_heading_is_the_engine_resolution_not_a_title_cased_plural() -> None:
    """The one key a client could plausibly re-derive and get wrong: ``"stories".title()`` is
    ``"Stories"``, and the markdown sq writes says ``"User Stories"``."""
    spec = load_workflow_spec()
    story = next(r for r in _subentity_kind_catalog(spec) if r["subentity_kind"] == "story")
    assert story["plural"] == "stories"
    assert story["container_heading"] == "User Stories"
    assert story["container_heading"] != str(story["plural"]).title()


# ─── an adopter who renames, re-prefixes and drops ──────────────────────────────


async def test_a_customized_squad_publishes_its_own_vocabulary(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    result = await invoke(["workflow", "subentity-kinds", "--json"])
    assert result.exit_code == 0, result.output
    rows = {r["subentity_kind"]: r for r in json.loads(result.output)}

    assert sorted(rows) == ["action", "observation", "story", "subtask"]
    assert "finding" not in rows

    observation = rows["observation"]
    assert observation["lifecycle"] == "finding"
    assert observation["plural"] == "observations"
    assert observation["local_prefix"] == "OB"
    assert observation["container_heading"] == "Observations"
    assert observation["completion"] == "WontFix"
    assert observation["maps_parent_story"] is False
    assert observation["fields"] == [
        {"code": "impact", "label": "Blast radius", "collection": "impact"}
    ]

    action = rows["action"]
    assert action["lifecycle"] == "action"
    assert action["local_prefix"] == "AC"
    assert action["completion"] == "Actioned"
    assert action["maps_parent_story"] is True
    assert action["fields"] == []


async def test_a_renamed_plural_drags_the_container_heading_with_it(project, invoke) -> None:
    """``story`` keeps its name but changes its plural: the bundled special-case heading is
    keyed on the KIND, so it still wins — the point being that the published value is whatever
    the engine writes into the file, never the client's own guess."""
    _write_override(project.squad_dir, _CUSTOMIZED)
    result = await invoke(["workflow", "subentity-kinds", "--json"])
    rows = {r["subentity_kind"]: r for r in json.loads(result.output)}
    spec = load_workflow_spec(squad_dir=project.squad_dir)
    assert rows["story"]["plural"] == "epics_stories"
    assert rows["story"]["container_heading"] == spec.subentity_container_heading("story")


async def test_the_type_row_joins_the_kind_catalog_in_a_customized_squad(project, invoke) -> None:
    """The chain a client walks: item.type -> type row -> subentity_kind -> kind row. It has
    to close on an adopter's own vocabulary, not just the bundled arrangement."""
    _write_override(project.squad_dir, _CUSTOMIZED)
    types = json.loads((await invoke(["workflow", "types", "--json"])).output)
    kinds = json.loads((await invoke(["workflow", "subentity-kinds", "--json"])).output)
    kind_rows = {r["subentity_kind"]: r for r in kinds}

    by_type = {r["type"]: r for r in types}
    assert by_type["review"]["subentity_kind"] == "observation"
    assert by_type["incident"]["subentity_kind"] == "action"
    assert by_type["epic"]["subentity_kind"] is None

    for row in types:
        referenced = row["subentity_kind"]
        assert referenced is None or referenced in kind_rows

    # …and the declared label a preview renders is reachable at the end of it.
    assert kind_rows[by_type["review"]["subentity_kind"]]["fields"][0]["label"] == "Blast radius"


async def test_the_type_rows_lifecycle_names_the_custom_machine(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    types = {
        r["type"]: r for r in json.loads((await invoke(["workflow", "types", "--json"])).output)
    }
    kinds = {
        r["subentity_kind"]: r
        for r in json.loads((await invoke(["workflow", "subentity-kinds", "--json"])).output)
    }
    assert types["incident"]["lifecycle"] == "work"
    assert kinds["action"]["lifecycle"] == "action"


async def test_the_frozen_key_set_holds_on_a_customized_squad_too(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    rows = json.loads((await invoke(["workflow", "subentity-kinds", "--json"])).output)
    for row in rows:
        assert list(row) == list(SUBENTITY_KIND_CATALOG_FIELDS)
        for entry in row["fields"]:
            assert list(entry) == list(FIELD_ENTRY_FIELDS)


async def test_the_human_table_renders_the_customized_vocabulary(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    result = await invoke(["workflow", "subentity-kinds"])
    assert result.exit_code == 0, result.output
    for token in ("observation", "observations", "OB", "WontFix", "impact", "action", "AC"):
        assert token in result.output
