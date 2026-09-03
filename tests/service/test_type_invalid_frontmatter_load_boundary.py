"""Falsifies `Item.from_frontmatter`'s load-boundary guarantee as a *shape sweep*, not one
example per exception type it happens to catch.

The guarantee, in its own words: whatever is wrong with a file's data, every caller sees one
`SquadsError` naming the path -- never a raw builtin or third-party exception. A boundary is only
as good as the widest input class it has actually been driven against, and the failure mode that
motivates this module is a boundary that looks correct because the single shape it was tested with
happened to route through the one validator that was wired up (`title` as a list reaches pydantic;
`labels: 5`, `refs: 5`, `extra: oops`, `subentities: [5]` and `created_at: not-a-date` did not, and
threw `TypeError`/`ValueError` straight past it).

So this is table-driven over **frontmatter field x wrong type**, and the table's field coverage is
itself asserted against `Item`'s own model fields -- adding a field to the model fails this module
until a shape for it exists, which is the part a hand-listed table cannot do for itself.

Every shape is driven through **three** independent surfaces, because widening the boundary widened
its blast radius: the two corpus scanners (`check`, `repair`) and the single-item verbs, which now
reach the same boundary for one corrupt file and previously could only ever be hit via a scan.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._models import _item as item_module
from squads._models._item import Item
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


def _set_frontmatter_value(path: Path, key: str, value: object) -> None:
    """Plant *value* under *key* in the file's frontmatter, bypassing the service entirely.

    Re-dumps through `join_frontmatter`, so the block stays valid YAML and every shape below is
    genuinely "parses as YAML, then fails to become an Item" -- not a YAML failure wearing a
    different hat (the read/parse-guard family has its own suite).
    """
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    fm[key] = value
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


def _reload(svc, item) -> Item:
    """`Item.from_frontmatter` against the item's file as it now sits on disk -- the boundary
    itself, with no command around it."""
    path = svc.paths.abspath(item.path)
    return Item.from_frontmatter(
        split_frontmatter(path.read_text(encoding="utf-8"))[0],
        path=item.path,
        default_kind=svc.spec.default_ref_kind(),
    )


#: One entry per (frontmatter field, wrong type). Several fields carry more than one, because the
#: *container* shapes fail at different depths: `refs: 5` fails on the container, `refs: [5]` on an
#: element, and a fix for one is not a fix for the other -- the original defect shipped with the
#: element case working and the container case throwing.
_INVALID_SHAPES: list[tuple[str, str, object]] = [
    ("id_int", "id", 5),
    ("id_list", "id", ["TASK", "9"]),
    ("sequence_id_str", "sequence_id", "eleven"),
    ("type_int", "type", 5),
    ("title_list", "title", ["a", "b"]),
    ("title_int", "title", 5),
    ("slug_int", "slug", 5),
    ("status_int", "status", 5),
    ("description_int", "description", 5),
    ("parent_int", "parent", 5),
    ("author_int", "author", 5),
    ("assignee_int", "assignee", 5),
    ("priority_int", "priority", 5),
    ("severity_int", "severity", 5),
    ("labels_int", "labels", 5),
    ("labels_int_element", "labels", [5]),
    ("labels_mapping", "labels", {"a": 1}),
    ("refs_int", "refs", 5),
    ("refs_int_element", "refs", [5]),
    ("refs_mapping", "refs", {"a": 1}),
    ("subentities_int", "subentities", 5),
    ("subentities_str", "subentities", "oops"),
    ("subentities_mapping", "subentities", {"a": 1}),
    ("subentities_int_element", "subentities", [5]),
    ("subentities_no_local_id", "subentities", [{"status": "Todo"}]),
    ("subentities_no_status", "subentities", [{"local_id": "ST1"}]),
    ("subentities_status_int", "subentities", [{"local_id": "ST1", "status": 5}]),
    ("title_empty", "title", ""),
    ("subentities_extra_str", "subentities", [{"local_id": "ST1", "status": "Todo", "extra": "x"}]),
    ("created_at_unparseable", "created_at", "not-a-date"),
    ("updated_at_unparseable", "updated_at", "not-a-date"),
    ("created_session_int", "created_session", 5),
    ("modified_session_int", "modified_session", 5),
    ("extra_str", "extra", "oops"),
    ("extra_list", "extra", [1, 2]),
    ("extra_non_str_key", "extra", {5: "a"}),
]
_SHAPE_IDS = [name for name, _, _ in _INVALID_SHAPES]
_SHAPE_ARGS = [(key, value) for _, key, value in _INVALID_SHAPES]

#: The two `Item` fields no frontmatter key ever supplies, so no shape is owed for them: `path` is
#: passed by the caller (never read from the file), and `prefix` is derived from `id` and
#: deliberately not read even when a legacy file carries the key.
_NOT_FROM_FRONTMATTER = frozenset({"path", "prefix"})

#: Frontmatter keys that carry no `Item` field of their own. `id` is the durable human id -- a
#: computed field on the way out, plain input data on the way in.
_FRONTMATTER_ONLY_KEYS = frozenset({"id"})


def test_the_shape_table_covers_every_frontmatter_field_the_boundary_reads():
    """The table's own coverage guard, and the reason this module is not merely a longer list of
    examples: a shape sweep is only a sweep while nothing has been added behind its back. A new
    `Item` field reaches the boundary the moment it is declared, so this fails until the table
    names it -- the omission is caught here, not on a corrupt file in someone's repo."""
    expected = (frozenset(Item.model_fields) - _NOT_FROM_FRONTMATTER) | _FRONTMATTER_ONLY_KEYS
    covered = {key for _, key, _ in _INVALID_SHAPES}
    assert expected - covered == frozenset(), (
        "every frontmatter field the load boundary reads needs at least one wrong-type shape; "
        f"uncovered: {sorted(expected - covered)}"
    )
    assert covered - expected == frozenset(), (
        f"the table names fields the boundary does not read: {sorted(covered - expected)}"
    )


@pytest.mark.parametrize(("key", "value"), _SHAPE_ARGS, ids=_SHAPE_IDS)
async def test_the_boundary_itself_refuses_every_type_invalid_shape(svc, key, value):
    """The narrowest surface, asserted first so the two command-level tests below cannot pass by
    accident on a shape the boundary silently *accepts*. `SquadsError` specifically -- a builtin
    escaping is a failure, and `pytest.raises(Exception)` would have hidden all six original
    escapes."""
    item = (await create_item(svc, "task", "a task with a type-invalid field")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), key, value)

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    assert item.path in str(exc.value)


@pytest.mark.parametrize(("key", "value"), _SHAPE_ARGS, ids=_SHAPE_IDS)
async def test_check_reports_a_type_invalid_field_and_keeps_scanning(svc, key, value):
    """`check` must name the corrupt file *and* still report an unrelated issue on a different
    file. Asserting only the first half would pass against a boundary that reports the bad file
    and then aborts -- which is exactly what the malformed-`id` shape did."""
    good = (await create_item(svc, "task", "an unrelated task with its own problem")).item
    good_path = svc.paths.abspath(good.path)
    good_path.write_text(
        good_path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", ""),
        encoding="utf-8",
    )
    bad = (await create_item(svc, "task", "a task with a type-invalid field")).item
    bad_path = svc.paths.abspath(bad.path)
    _set_frontmatter_value(bad_path, key, value)

    issues = await svc.check()

    assert any(i.level == "error" and bad_path.name in i.item for i in issues), (
        f"the corrupt file must be named at error level, got: {issues}"
    )
    assert any("sq:body" in i.message for i in issues), (
        f"the scan must have continued past the corrupt file, got: {issues}"
    )


@pytest.mark.parametrize(("key", "value"), _SHAPE_ARGS, ids=_SHAPE_IDS)
async def test_repair_reports_a_type_invalid_field_and_carries_the_entry_forward(svc, key, value):
    """`repair`'s half of the same contract: reported, never a traceback, and the item stays
    resolvable from its previous index entry rather than vanishing."""
    bad = (await create_item(svc, "task", "a task with a type-invalid field")).item
    before = await svc.get(bad.id)
    bad_path = svc.paths.abspath(bad.path)
    _set_frontmatter_value(bad_path, key, value)

    result = await svc.repair()

    assert any(bad_path.name in msg for msg in result.unreadable), result.unreadable
    assert bad.id not in result.missing_ids, "carried forward, not missing"
    assert (await svc.get(bad.id)).title == before.title


#: The single-item verbs. Before the boundary moved into `from_frontmatter` only a scan could reach
#: it; afterwards every one of these does, for the corrupt item's own operations -- so the widened
#: blast radius is driven rather than assumed to be covered by `check`/`repair`. Every slug used is
#: `manager`, the one role the `minimal` fixture roster carries: an unknown slug would raise its own
#: `SquadsError` before the file is ever read and make the assertion vacuous.
_SINGLE_ITEM_VERBS: list[tuple[str, Callable[[Any, str], Any]]] = [
    ("status", lambda svc, item_id: svc.set_status(item_id, "InProgress")),
    ("update", lambda svc, item_id: svc.update(item_id, assignee="manager")),
    ("body", lambda svc, item_id: svc.set_body(item_id, "a new body")),
    ("comment", lambda svc, item_id: svc.comment(item_id, ["a note"], as_slug="manager")),
    ("add_subtask", lambda svc, item_id: svc.add_subtask(item_id, "a subtask")),
    ("retype", lambda svc, item_id: svc.retype(item_id, "bug")),
]
_VERB_IDS = [name for name, _ in _SINGLE_ITEM_VERBS]
_VERB_FNS = [fn for _, fn in _SINGLE_ITEM_VERBS]


@pytest.mark.parametrize(("key", "value"), _SHAPE_ARGS, ids=_SHAPE_IDS)
@pytest.mark.parametrize("verb", _VERB_FNS, ids=_VERB_IDS)
async def test_a_single_item_verb_on_a_type_invalid_file_fails_at_the_load_boundary(
    svc, verb, key, value
):
    """Two assertions, both load-bearing: `SquadsError` (a builtin escaping fails here) *and* the
    boundary's own wording, so a verb that happens to refuse for some unrelated reason cannot pass
    this by accident."""
    bad = (await create_item(svc, "task", "a task with a type-invalid field")).item
    _set_frontmatter_value(svc.paths.abspath(bad.path), key, value)

    with pytest.raises(SquadsError) as exc:
        await verb(svc, bad.id)

    assert "invalid item data" in str(exc.value)


async def test_a_healthy_sibling_still_works_while_another_item_is_type_invalid(svc):
    """The blast radius is the corrupt item's own operations and nothing more. Without this, the
    tests above are equally satisfied by a fix that refuses every verb on every item."""
    healthy = (await create_item(svc, "task", "a healthy task")).item
    bad = (await create_item(svc, "task", "a task with a type-invalid field")).item
    _set_frontmatter_value(svc.paths.abspath(bad.path), "labels", 5)

    assert (await svc.set_status(healthy.id, "Ready")).status == "Ready"


# ------------------------------------------------------- shapes the boundary tolerates on purpose


async def test_an_absent_timestamp_defaults_rather_than_failing(svc):
    """The one shape the boundary is *meant* to tolerate: a legacy file written before the field
    existed. Absent/null means "no timestamp recorded", not "corrupt", and must keep loading."""
    item = (await create_item(svc, "task", "a task predating the timestamp fields")).item
    path = svc.paths.abspath(item.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm.pop("created_at", None)
    fm["updated_at"] = None
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    loaded = _reload(svc, item)

    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at.tzinfo is not None


async def test_a_numeric_timestamp_is_read_as_an_epoch_rather_than_invented(svc):
    """Deliberately outside the refusal contract, and pinned so the choice is not accidental.

    A number is a shape pydantic accepts for a datetime (a Unix timestamp), so it loads. That is
    the better of the two tolerant options available: the value is at least derived from what the
    file says, where the previous behaviour silently substituted `now()` for *any* non-string and
    so made a corrupt timestamp indistinguishable from a freshly written one.
    """
    item = (await create_item(svc, "task", "a task with a numeric timestamp")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), "created_at", 5)

    assert _reload(svc, item).created_at == datetime(1970, 1, 1, 0, 0, 5, tzinfo=UTC)


#: Every container-valued frontmatter key the replaced coercions covered, with the empty value each
#: one means when unset. All four, not two: the old expressions were `list(... or [])` for `labels`
#: and `refs`, `[s for s in (... or [])]` for `subentities` and `dict(... or {})` for `extra`, and
#: every one of those `or`s swallowed `""`. Parametrizing the compatibility rule over a subset is
#: what let two of the four regress while the rule's own docstring claimed the whole scope.
_CONTAINER_FIELDS: list[tuple[str, object]] = [
    ("labels", []),
    ("refs", []),
    ("subentities", []),
    ("extra", {}),
]
_CONTAINER_IDS = [key for key, _ in _CONTAINER_FIELDS]


def test_the_container_table_covers_every_container_field_the_boundary_folds():
    """The table's own coverage guard, for the same reason the shape table above has one: a fifth
    container field would otherwise be added with no compatibility shape and nothing would say so.
    Derived from `Item`'s own annotations rather than hand-listed."""
    covered = {key for key, _ in _CONTAINER_FIELDS}
    declared = {
        name
        for name, f in Item.model_fields.items()
        if name not in _NOT_FROM_FRONTMATTER
        and getattr(f.annotation, "__origin__", f.annotation) in (list, dict)
    }
    assert declared == covered, f"container fields not covered: {sorted(declared - covered)}"


@pytest.mark.parametrize(("key", "empty"), _CONTAINER_FIELDS, ids=_CONTAINER_IDS)
@pytest.mark.parametrize("value", [None, ""], ids=["null", "empty_string"])
async def test_an_unset_container_field_still_loads_as_empty(svc, key, value, empty):
    """Compatibility, and the reason it is pinned across the whole scope rather than left to chance.

    The coercions this replaced defaulted through an `or`, which swallowed `""` as well as `None` --
    so a file carrying `labels: ''`, `subentities: ''` or `extra: ''` loaded. Tightening any of them
    would mean a file that loaded yesterday failing today, which is the wrong direction for a
    boundary whose job is keeping legacy files readable. A *non-empty* string is a different matter
    and is rejected below, rather than silently exploded into one entry per character the way
    `list("abc")` did.

    The asymmetry is the defect, not the strictness: whichever way the rule goes it has to go the
    same way for all four keys, since they are equally reachable (only by a hand-edit or a merge
    artifact -- `to_frontmatter_dict` omits every one of them when empty).
    """
    item = (await create_item(svc, "task", "a task with an unset container field")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), key, value)

    assert getattr(_reload(svc, item), key) == empty


@pytest.mark.parametrize("key", _CONTAINER_IDS)
async def test_a_bare_string_container_field_is_rejected_rather_than_coerced(svc, key):
    """The old `list("abc")` turned one hand-written value into three, and nothing ever said so.
    Rejecting is both correct and louder; it is asserted for all four keys so the compatibility
    carve-out above cannot quietly widen into accepting any string at all in any of them."""
    item = (await create_item(svc, "task", "a task with a bare string container field")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), key, "abc")

    with pytest.raises(SquadsError):
        _reload(svc, item)


async def test_a_naive_timestamp_is_normalised_to_utc(svc):
    """The tz normalisation the old hand-rolled parse did, kept: a hand-written timestamp with no
    offset must not come back naive, or every downstream comparison against an aware `now()`
    raises."""
    item = (await create_item(svc, "task", "a task with a naive timestamp")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), "created_at", "2026-01-02T03:04:05")

    assert _reload(svc, item).created_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


# ------------------------------------------------------- what the refusal actually says out loud

#: Fragments of pydantic's own dump that must never reach an operator. `str(exc)` carries all four:
#: a link to a library the adopter did not install and cannot act on, the machine tail, and -- for
#: a model-level validator -- a truncated `repr` of every other field in the file, which buries the
#: one field that is wrong under the ones that are fine.
_PYDANTIC_LEAKS: list[str] = [
    "errors.pydantic.dev",
    "input_value=",
    "input_type=",
    "validation error for",
]


@pytest.mark.parametrize(("key", "value"), _SHAPE_ARGS, ids=_SHAPE_IDS)
async def test_no_shape_leaks_pydantics_own_dump_into_the_message(svc, key, value):
    """Swept over the whole shape table rather than the one or two shapes that motivated it, because
    the leak is per *error kind*, not per field: a container error, an element error, a nested
    sub-entity error and a model-level `before` validator each render differently, and checking one
    proves nothing about the others.

    This is a direct consequence of making `model_validate` the single failure channel -- correct
    in itself, but it means the text is whatever pydantic says unless the boundary renders it,
    where the hand-rolled coercions it replaced at least failed in project vocabulary.
    """
    item = (await create_item(svc, "task", "a task with a type-invalid field")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), key, value)

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    message = str(exc.value)
    for leak in _PYDANTIC_LEAKS:
        assert leak not in message, f"{leak!r} leaked into: {message}"


async def test_the_message_names_the_offending_field_and_what_was_wrong_with_it(svc):
    """The usable half has to survive the tidying, or this traded a noisy message for a useless
    one. The field name plus the reason was the middle line of five in the dump; it is now the
    whole message."""
    item = (await create_item(svc, "task", "a task with a type-invalid field")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), "labels", 5)

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    message = str(exc.value)
    assert "labels" in message
    assert "list" in message
    assert "int" in message, "the type it got is what makes the message actionable"


async def test_every_bad_field_is_named_not_just_the_first(svc):
    """`exc.errors()` is a list and the rendering has to stay one: reporting only the first bad
    field would send an operator round the loop once per field, and the previous dump did name them
    all."""
    item = (await create_item(svc, "task", "a task with two type-invalid fields")).item
    path = svc.paths.abspath(item.path)
    _set_frontmatter_value(path, "labels", 5)
    _set_frontmatter_value(path, "title", ["a", "b"])

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    assert "labels" in str(exc.value)
    assert "title" in str(exc.value)


async def test_a_nested_sub_entity_field_is_addressed_by_its_path(svc):
    """A sub-entity error's `loc` is a tuple, not a name, and flattening it to the first element
    would report a whole `subentities` list as invalid when one field of one entry is."""
    item = (await create_item(svc, "task", "a task with a bad sub-entity field")).item
    _set_frontmatter_value(
        svc.paths.abspath(item.path), "subentities", [{"local_id": "ST1", "status": 5}]
    )

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    assert "subentities.0.status" in str(exc.value)


#: Shapes whose rendered clause must NOT carry the "(got <type>)" suffix, keyed by pydantic error
#: *kind* rather than guessed per shape: a genuine type mismatch (a kind ending `_type`/`_parsing`)
#: gets it, everything else does not. That covers our own `value_error`/`assertion_error` (whose
#: message already names what it got), a nested `missing` field (`input` is the *enclosing
#: mapping*, not the absent value -- the field has none, that being the fault), and a constraint
#: kind like `string_too_short` (already says "string" in its own sentence).
_NO_SUFFIX_SHAPES = frozenset(
    {
        "id_int",
        "id_list",
        "type_int",
        "status_int",
        "subentities_status_int",
        "subentities_no_local_id",
        "subentities_no_status",
        "title_empty",
    }
)


@pytest.mark.parametrize(("name", "key", "value"), _INVALID_SHAPES, ids=_SHAPE_IDS)
async def test_the_got_type_suffix_is_appended_only_for_a_genuine_type_mismatch(
    svc, name, key, value
):
    """The suffix used to key on error *provenance* (ours vs pydantic's) rather than on whether
    the type is the missing information, and misfired on two shapes: a nested `missing` field
    read as "(got dict)" -- describing a value the operator never wrote, the field having none
    being the fault -- and a `string_too_short` stuttering "(got str)" after its own sentence
    already said "string". Swept over the whole table, not just the shapes that motivated the
    fix, because a predicate that reads elegant and drops a useful `(got ...)` from a genuine
    mismatch is worse than the stutter it was meant to fix.
    """
    item = (await create_item(svc, "task", "a task with a type-invalid field")).item
    _set_frontmatter_value(svc.paths.abspath(item.path), key, value)

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    message = str(exc.value)
    if name in _NO_SUFFIX_SHAPES:
        assert "(got " not in message, f"stutter/omission-as-value suffix leaked into: {message}"
    else:
        assert "(got " in message, f"a genuine type mismatch lost its (got ...) suffix: {message}"


async def test_f15s_regressed_shapes_render_the_exact_clause_the_finding_quoted(svc):
    """Pinned verbatim rather than by predicate alone: the sweep above proves the general rule
    holds across the whole shape table, this pins the specific three clauses the finding read
    wrong. A missing sub-entity field must read as an omission, and an empty title must not
    repeat that it is a string.
    """
    item = (await create_item(svc, "task", "a task with the shapes the finding flagged")).item
    path = svc.paths.abspath(item.path)
    _set_frontmatter_value(path, "subentities", [{}])
    _set_frontmatter_value(path, "title", "")

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    message = str(exc.value)
    assert "subentities.0.local_id: Field required" in message
    assert "subentities.0.status: Field required" in message
    assert "title: String should have at least 1 character" in message
    assert "(got" not in message


# ------------------------------------------------------------------- the required-key half


@pytest.mark.parametrize("key", ["type", "sequence_id", "status"])
async def test_a_missing_required_key_names_the_key_and_the_path(svc, key):
    """The other failure channel: the required keys are read by name up front, so `KeyError` never
    has to be caught at the boundary -- and the operator is told *which* key is gone rather than
    reading a bare `KeyError` repr."""
    item = (await create_item(svc, "task", "a task missing a required key")).item
    path = svc.paths.abspath(item.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm.pop(key)
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    with pytest.raises(SquadsError) as exc:
        _reload(svc, item)

    assert key in str(exc.value)
    assert item.path in str(exc.value)


async def test_an_internal_key_error_is_not_relabelled_as_invalid_file_data(monkeypatch, svc):
    """The narrowing's actual subject, which no corrupt-file shape can reach.

    `KeyError` is this codebase's usual symptom of an internal spec-lookup miss, not of bad file
    data. While the boundary caught it, one raised by anything on its call graph would have been
    reported to the operator as "invalid item data in <path>", sending them to hand-edit a file
    that is fine -- and `repair` would have third-stated the item and carried a stale entry
    forward instead of failing loudly. Simulated by making one helper on that call graph raise,
    since nothing there does a spec lookup today: the point is what the boundary does with it, not
    that a live site exists.
    """
    item = (await create_item(svc, "task", "a healthy task")).item
    path = svc.paths.abspath(item.path)
    data = split_frontmatter(path.read_text(encoding="utf-8"))[0]

    def _boom(_data: dict[str, Any]) -> Any:
        raise KeyError("story")

    monkeypatch.setattr(item_module, "_read_extra", _boom)

    with pytest.raises(KeyError):
        Item.from_frontmatter(data, path=item.path, default_kind=svc.spec.default_ref_kind())
