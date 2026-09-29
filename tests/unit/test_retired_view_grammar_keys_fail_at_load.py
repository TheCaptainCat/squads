"""The projection layer's declaration grammar — ``[views.<name>].fields``/``group_by``/
``order_by`` and ``items.<type>.views`` — is retired: a spec that still declares any of the
four keys fails at load with an error naming the exact key it found and saying it was
**retired**, not a generic ``unknown key`` (the wording every genuinely-unrecognised key gets)
and never the self-splat position's ``brand-new key`` wording — both of which name the wrong
direction of change for a key that was declared, shipped, and then removed.

Table-driven across every shape a 0.14 override could still carry one of these keys in: each
of the six declared source kinds, a plain assignment, an inline table, a splat token in value
position, the key nested under ``source`` rather than directly under the view, and
``items.<type>.views`` both populated and empty. The check runs on the raw, pre-merge document
— before splat resolution ever gets a chance to call a retired key ``brand-new`` — so none of
these shapes reaches ``ViewSpec``/``ItemSpec``'s own generic ``extra="forbid"`` at all.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec
from squads._workflow._loader import lint_workflow_spec

_SOURCE_KINDS = {
    "ref": '{ kind = "ref", name = "related" }',
    "subentity": '{ kind = "subentity", name = "story" }',
    "subtree": '{ kind = "subtree", name = "task" }',
    "role": '{ kind = "role" }',
    "playbook": '{ kind = "playbook" }',
    "self": '{ kind = "self" }',
}

_RETIRED_VALUE = {
    "fields": '[ { code = "id", label = "Id" } ]',
    "group_by": '"status"',
    "order_by": '["id"]',
}


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _assert_retired_not_unknown(message: str, key: str) -> None:
    assert f"'{key}'" in message
    assert "retired" in message
    assert "unknown key" not in message
    assert "brand-new" not in message


# --------------------------------------------------------------------------- view keys, by source


@pytest.mark.parametrize("source_kind", sorted(_SOURCE_KINDS))
@pytest.mark.parametrize("key", sorted(_RETIRED_VALUE))
def test_a_view_declaring_a_retired_key_fails_at_load_naming_it_retired(
    tmp_path: Path, source_kind: str, key: str
) -> None:
    _write_override(
        tmp_path,
        f"""
[views.probe]
source = {_SOURCE_KINDS[source_kind]}
{key} = {_RETIRED_VALUE[key]}
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    _assert_retired_not_unknown(str(excinfo.value), key)


def test_fields_gets_its_own_reason_not_the_grouping_and_ordering_one(tmp_path: Path) -> None:
    """``fields`` chose and labelled columns — a different job from what ``group_by``/
    ``order_by`` did. Reusing their "grouping and ordering" sentence for ``fields`` would
    misdescribe it, so each retired key states what it did, not a shared one."""
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "self" }
fields = [ { code = "id", label = "Id" } ]
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(excinfo.value)
    assert "column" in message
    assert "grouping" not in message
    assert "ordering" not in message


@pytest.mark.parametrize("key", ["group_by", "order_by"])
def test_group_by_and_order_by_keep_their_own_reason_not_the_fields_one(
    tmp_path: Path, key: str
) -> None:
    _write_override(
        tmp_path,
        f"""
[views.probe]
source = {{ kind = "self" }}
{key} = {_RETIRED_VALUE[key]}
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(excinfo.value)
    assert "column" not in message


# --------------------------------------------------------------------------- alternate shapes


def test_a_retired_key_as_an_inline_table_assignment_is_still_caught(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        'views.probe = { source = { kind = "self" }, '
        'fields = [ { code = "id", label = "Id" } ] }\n',
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    _assert_retired_not_unknown(str(excinfo.value), "fields")


def test_a_retired_key_in_splat_token_position_is_named_retired_not_brand_new(
    tmp_path: Path,
) -> None:
    """The self-splat form ``fields = ["$(*self)", ...]`` is exactly what
    :func:`~squads._specmerge.resolve_splat_refs` would otherwise refuse with "a brand-new key
    has no bundled list to append to" — backwards for a key that used to be bundled. This check
    runs before splat resolution ever sees it."""
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "self" }
fields = ["$(*self)", { code = "id", label = "Id" }]
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    _assert_retired_not_unknown(str(excinfo.value), "fields")


def test_items_views_in_splat_token_position_is_named_retired_not_brand_new(
    tmp_path: Path,
) -> None:
    _write_override(tmp_path, 'items.bug.views = ["$(*self)", "milestone_rollup"]\n')
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    _assert_retired_not_unknown(str(excinfo.value), "views")


def test_a_retired_key_nested_under_source_is_still_caught(tmp_path: Path) -> None:
    """A retired key hand-typed inside the ``source`` table is still a mistaken 0.14 key, not
    a new mistake ``ViewSource``'s own ``extra="forbid"`` should have to explain."""
    _write_override(
        tmp_path,
        """
[views.probe.source]
kind = "ref"
name = "related"
group_by = "status"
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(excinfo.value)
    assert "views.probe.source.group_by" in message
    _assert_retired_not_unknown(message, "group_by")


# --------------------------------------------------------------------------- items.<type>.views


@pytest.mark.parametrize("item_type", ["milestone", "bug"])
def test_an_item_type_declaring_views_fails_at_load_naming_the_key(
    tmp_path: Path, item_type: str
) -> None:
    _write_override(tmp_path, f'[items.{item_type}]\nviews = ["milestone_rollup"]\n')
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    _assert_retired_not_unknown(str(excinfo.value), "views")


def test_an_empty_items_views_list_still_fails_at_load(tmp_path: Path) -> None:
    """Presence of the key is what is retired, not any particular non-empty value — an adopter
    who ran a mechanical find/replace that left ``views = []`` behind still needs to hear
    about it."""
    _write_override(tmp_path, "[items.milestone]\nviews = []\n")
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    _assert_retired_not_unknown(str(excinfo.value), "views")


# --------------------------------------------------------------------------- combined + lint


def test_all_four_retired_keys_declared_together_are_each_named_in_one_error(
    tmp_path: Path,
) -> None:
    """A spec carrying more than one retired key at once — the realistic shape of an unedited
    0.14 override — names every offending key in one raise, not just the first."""
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" } ]
group_by = "status"
order_by = ["id"]

[items.milestone]
views = ["milestone_rollup"]
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(excinfo.value)
    for key in ("fields", "group_by", "order_by", "views"):
        assert f"'{key}'" in message
    assert "unknown key" not in message
    assert "brand-new" not in message


def test_lint_reports_a_retired_key_with_a_fix_hint_that_does_not_say_add_it_back(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "self" }
group_by = "status"
""",
    )
    findings = lint_workflow_spec(tmp_path)
    assert findings
    level, location, message, hint = findings[0]
    assert level == "error"
    assert "retired" in message
    assert "'group_by'" in message
    assert "add it back" not in hint
    # The generic row this replaced named the view; an adopter with several views declared
    # cannot tell which one to fix from ".overrides/workflow.toml" alone.
    assert "views.probe" in location


def test_lint_names_the_offending_view_for_each_of_several_retired_keys(tmp_path: Path) -> None:
    """Two views, each with their own retired key — every finding's location must point back
    at its own view, not a shared, undifferentiated file path."""
    _write_override(
        tmp_path,
        """
[views.probe_a]
source = { kind = "self" }
group_by = "status"

[views.probe_b]
source = { kind = "self" }
order_by = ["id"]
""",
    )
    findings = lint_workflow_spec(tmp_path)
    locations = {location for _level, location, _message, _hint in findings}
    assert "views.probe_a.group_by" in locations
    assert "views.probe_b.order_by" in locations


def test_lint_names_the_offending_type_for_a_retired_items_views_key(tmp_path: Path) -> None:
    _write_override(tmp_path, '[items.bug]\nviews = ["milestone_rollup"]\n')
    findings = lint_workflow_spec(tmp_path)
    assert findings
    _level, location, _message, _hint = findings[0]
    assert "items.bug" in location


def test_the_items_views_hint_names_the_placement_verb_not_a_refused_body_edit(
    tmp_path: Path,
) -> None:
    """'Place the tag in the body' reads as an instruction to type it there, and a body-marker
    tag is refused by ``reject_markers``. The supported route is the placement verb."""
    _write_override(tmp_path, '[items.bug]\nviews = ["milestone_rollup"]\n')
    findings = lint_workflow_spec(tmp_path)
    assert findings
    _level, _location, _message, hint = findings[0]
    assert "view add" in hint
    assert "template/body" not in hint

    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    assert "view add" in str(excinfo.value)
    assert "template/body" not in str(excinfo.value)
