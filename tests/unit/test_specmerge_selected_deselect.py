"""The `[selected]` deselect: apply the surviving-set shrink, strip the `[selected]` table
from the returned mapping, and record provenance for every key it dropped."""

from _helpers import SPECMERGE_WORKFLOW_SECTIONS as WORKFLOW_SECTIONS
from squads._specmerge import Deselection, apply_selected


def test_a_selected_list_leaves_exactly_the_named_keys_and_drops_the_rest() -> None:
    merged = {
        "items": {"epic": {}, "feature": {}, "task": {}, "guide": {}},
        "selected": {"items": ["epic", "feature", "task"]},
    }

    result, _deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert violations == []
    assert set(result["items"]) == {"epic", "feature", "task"}


def test_the_selected_table_is_absent_from_the_returned_mapping() -> None:
    merged = {"items": {"epic": {}}, "selected": {"items": ["epic"]}}

    result, _deselections, _violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert "selected" not in result


def test_provenance_names_each_dropped_key_against_the_section_that_dropped_it() -> None:
    merged = {
        "items": {"epic": {}, "feature": {}, "guide": {}},
        "selected": {"items": ["epic", "feature"]},
    }

    _result, deselections, _violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert set(deselections) == {Deselection("items", "guide")}


def test_multiple_sections_each_record_their_own_dropped_keys() -> None:
    merged = {
        "items": {"epic": {}, "guide": {}},
        "statuses": {"Draft": {}, "Weird": {}},
        "selected": {"items": ["epic"], "statuses": ["Draft"]},
    }

    _result, deselections, _violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert set(deselections) == {Deselection("items", "guide"), Deselection("statuses", "Weird")}


def test_no_selected_table_is_a_no_op() -> None:
    merged = {"items": {"epic": {}}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert result == merged
    assert deselections == ()
    assert violations == []


def test_an_unknown_selected_section_key_fails_closed_naming_the_key_and_the_accepted_set() -> None:
    merged = {"items": {"epic": {}}, "selected": {"widgets": ["epic"]}}

    _result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "override.toml")

    assert deselections == ()
    assert len(violations) == 1
    assert "widgets" in violations[0].reason
    assert violations[0].origin == "override.toml"
    for name in sorted(WORKFLOW_SECTIONS):
        assert name in violations[0].hint


def test_several_unknown_section_keys_are_all_reported_together() -> None:
    merged = {"selected": {"widgets": ["a"], "gadgets": ["b"]}}

    _result, _deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    reported = {v.path for v in violations}
    assert reported == {"selected.widgets", "selected.gadgets"}


def test_an_entry_naming_a_key_absent_from_the_merged_section_fails_closed() -> None:
    """A keep-list entry that matches nothing is the deselect's one unbacked failure mode.

    It passes every shape check, drops the key it meant to keep, and leaves a spec that is
    perfectly valid — so no floor, referential or live-index check downstream can ever see it:
    they all inspect the spec that resulted, never the one that was asked for. Same argument
    the module already applies one level up to a mis-shaped keep value.
    """
    merged = {"items": {"epic": {}}, "selected": {"items": ["epic", "never-existed"]}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert deselections == ()
    assert [v.path for v in violations] == ["selected.items.never-existed"]
    assert "never-existed" in violations[0].reason
    assert "epic" in violations[0].hint
    # The violation path returns the caller's own input untouched — `selected` still present.
    assert result is merged


def test_a_keep_list_naming_a_key_the_override_itself_added_is_accepted() -> None:
    """Adding a key and keeping it in one document must work: the entries are checked against
    the MERGED section, so a brand-new type is already present by the time this runs."""
    merged = {"items": {"epic": {}, "widget": {}}, "selected": {"items": ["widget"]}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert violations == []
    assert deselections == (Deselection("items", "epic"),)
    assert result["items"] == {"widget": {}}


def test_a_selected_entry_for_a_section_absent_from_the_merged_mapping_is_inert() -> None:
    merged = {"selected": {"roles": ["python-dev"]}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert violations == []
    assert deselections == ()
    assert "selected" not in result


def test_a_bare_string_keep_value_fails_closed_instead_of_matching_no_key() -> None:
    """The obvious typo for `items = ["task"]` — `items = "task"` — must never reach
    `set(keep)`: as a set of characters it matches no real key, so every item type
    (including `task`) would otherwise be silently dropped."""
    merged = {"items": {"task": {}, "epic": {}}, "selected": {"items": "task"}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "override.toml")

    assert deselections == ()
    assert len(violations) == 1
    assert violations[0].path == "selected.items"
    assert "must be a list" in violations[0].reason
    # nothing was dropped — the merged mapping is untouched, `selected` included
    assert result == merged


def test_a_non_string_element_in_a_keep_list_fails_closed() -> None:
    merged = {"items": {"task": {}}, "selected": {"items": ["task", 1]}}

    _result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert deselections == ()
    assert len(violations) == 1
    assert violations[0].path == "selected.items"
    assert "list of strings" in violations[0].reason


def test_a_non_table_selected_value_fails_closed_naming_what_is_actually_wrong() -> None:
    merged = {"items": {"task": {}}, "selected": "items"}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert deselections == ()
    assert len(violations) == 1
    assert "[selected] must be a table" in violations[0].reason
    assert result == merged


def test_several_shape_violations_across_sections_are_reported_together() -> None:
    merged = {
        "items": {"task": {}},
        "statuses": {"Draft": {}},
        "selected": {"items": "task", "statuses": ["Draft", 1]},
    }

    _result, _deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    reported = {v.path for v in violations}
    assert reported == {"selected.items", "selected.statuses"}


def test_a_section_present_but_shaped_as_a_list_fails_closed_instead_of_doing_nothing() -> None:
    """The one deselect failure mode no downstream check can ever see: a drop that never
    happened leaves a *valid* spec, so nothing catches it unless the engine itself does. This
    is `roles.toml`'s own top-level shape — a list of tables, not a keyed table."""
    merged = {
        "roles": [{"slug": "manager"}, {"slug": "reviewer"}],
        "selected": {"roles": ["manager"]},
    }

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "override.toml")

    assert deselections == ()
    assert len(violations) == 1
    assert violations[0].path == "selected.roles"
    assert "not a table" in violations[0].reason
    assert "roles" in violations[0].reason
    # nothing was dropped — the merged mapping is untouched, both roles still present
    assert result == merged


def test_a_section_present_but_shaped_as_a_scalar_fails_closed() -> None:
    merged = {"items": 5, "selected": {"items": ["task"]}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert deselections == ()
    assert len(violations) == 1
    assert "int" in violations[0].reason
    assert result == merged


def test_a_section_absent_from_the_merged_mapping_stays_inert_not_a_violation() -> None:
    """The deliberate case must not regress under the new present-but-not-a-table check:
    absent stays inert, only present-but-not-a-table fails closed."""
    merged = {"selected": {"roles": ["x"]}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert violations == []
    assert deselections == ()
    assert "selected" not in result


def test_the_violation_path_returns_the_callers_own_input_completely_unmodified() -> None:
    """apply_selected's documented contract on the violation path: the exact object handed
    in, `selected` still present, nothing dropped — never a partially-applied result."""
    merged = {"items": {"task": {}}, "selected": {"nope": ["x"]}}

    result, deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert violations != []
    assert result is merged
    assert "selected" in result
    assert deselections == ()


def test_the_shrunk_result_keeps_the_sections_own_base_order_not_just_its_membership() -> None:
    """Every existing membership assertion in this file goes through `set(...)`, which cannot
    tell a reordered result from a correct one — pin the order explicitly."""
    merged = {
        "items": {"epic": {}, "feature": {}, "task": {}, "guide": {}},
        "selected": {"items": ["task", "epic", "feature"]},
    }

    result, _deselections, violations = apply_selected(merged, WORKFLOW_SECTIONS, "o")

    assert violations == []
    assert list(result["items"]) == ["epic", "feature", "task"]
