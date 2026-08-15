"""Deep recursive merge at leaf granularity: tables recurse per key, a leaf value (including
a plain array — always a leaf) replaces its counterpart wholesale, and an override declares
only what it changes."""

import importlib.resources
import tomllib
from typing import Any

from squads._specmerge import deep_merge


def _bundled_workflow() -> dict[str, Any]:
    pkg = importlib.resources.files("squads._specs")
    raw: dict[str, Any] = tomllib.loads((pkg / "workflow.toml").read_bytes().decode())
    return raw


def test_override_touching_one_field_leaves_every_other_field_of_that_entry_unchanged() -> None:
    base = {"items": {"task": {"prefix": "TASK", "folder": "tasks", "lifecycle": "work"}}}
    override = {"items": {"task": {"prefix": "TSK"}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    assert merged["items"]["task"]["prefix"] == "TSK"
    assert merged["items"]["task"]["folder"] == "tasks"
    assert merged["items"]["task"]["lifecycle"] == "work"


def test_plain_array_override_replaces_the_base_array_wholesale_with_no_element_unioned_in() -> (
    None
):
    base = {"items": {"task": {"validators": ["a", "b", "c"]}}}
    override = {"items": {"task": {"validators": ["z"]}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    assert merged["items"]["task"]["validators"] == ["z"]


def test_a_table_that_recurses_per_key_leaves_sibling_keys_of_the_nested_table_untouched() -> None:
    base = {
        "lifecycles": {
            "work": {
                "initial": "Draft",
                "transitions": {"Draft": ["Ready"], "Ready": ["InProgress"]},
            }
        }
    }
    override = {"lifecycles": {"work": {"transitions": {"Draft": ["Ready", "Cancelled"]}}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    assert merged["lifecycles"]["work"]["initial"] == "Draft"
    assert merged["lifecycles"]["work"]["transitions"]["Draft"] == ["Ready", "Cancelled"]
    assert merged["lifecycles"]["work"]["transitions"]["Ready"] == ["InProgress"]


def test_merging_an_empty_override_over_the_base_returns_a_mapping_equal_to_the_base() -> None:
    base = _bundled_workflow()

    merged, violations = deep_merge(base, {}, "o")

    assert violations == []
    assert merged == base


def test_a_brand_new_key_in_the_override_is_added_alongside_untouched_base_keys() -> None:
    base = {"items": {"task": {"prefix": "TASK"}}}
    override = {"items": {"widget": {"prefix": "WDG"}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    assert merged["items"]["task"] == {"prefix": "TASK"}
    assert merged["items"]["widget"] == {"prefix": "WDG"}


def test_the_merged_mapping_shares_no_mutable_structure_with_the_base() -> None:
    """The bundled base is a module-level immutable reused across every request; the merged
    document must be fully independent of it, including tables the override never touched —
    otherwise mutating the merged result mutates the base for the process lifetime."""
    base = {"items": {"task": {"prefix": "TASK"}}, "statuses": {"Draft": {"role": "pending"}}}

    merged, violations = deep_merge(base, {"statuses": {"Open": {"role": "active"}}}, "o")

    assert violations == []
    assert merged["items"] is not base["items"]
    assert merged["items"]["task"] is not base["items"]["task"]
    merged["items"]["task"]["prefix"] = "MUTATED"
    assert base["items"]["task"]["prefix"] == "TASK"


def test_an_untouched_base_list_is_independent_of_the_base() -> None:
    """The identity check above covers a dict; a list is the other mutable container type
    `deep_merge` must never share with the base, and it lives on a different code path (the
    untouched-key branch's `_bounded_deepcopy`, not the recursed-table branch)."""
    base = {"items": {"task": {"validators": ["a", "b"]}}}

    merged, violations = deep_merge(base, {"other": 1}, "o")

    assert violations == []
    assert merged["items"]["task"]["validators"] is not base["items"]["task"]["validators"]
    merged["items"]["task"]["validators"].append("mutated")
    assert base["items"]["task"]["validators"] == ["a", "b"]


def test_an_override_supplied_array_in_the_merged_result_is_independent_of_the_override() -> None:
    base = {"items": {"task": {"validators": ["a"]}}}
    override = {"items": {"task": {"validators": ["z"]}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    merged["items"]["task"]["validators"].append("mutated")
    assert override["items"]["task"]["validators"] == ["z"]


def test_key_order_is_base_order_with_override_only_keys_appended_in_override_order() -> None:
    """A shared key must stay wherever it sits in the base's own order — an override touching
    one field of one entry must never relocate that entry (or any sibling key) in the merged
    mapping's iteration order. Only genuinely new, override-only keys are appended, in the
    order the override declares them."""
    base = {"a": 1, "items": {"x": 1}, "z": 9}
    override = {"items": {"y": 2}, "brand_new": 3}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    assert list(merged) == ["a", "items", "z", "brand_new"]


def test_key_order_is_preserved_one_level_down_inside_a_recursed_table() -> None:
    base = {"items": {"x": {"p": 1}, "y": {"q": 2}}}
    override = {"items": {"x": {"p": 5}, "new": {"p": 3}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    assert list(merged["items"]) == ["x", "y", "new"]


def test_the_original_base_mapping_is_never_mutated_by_the_merge() -> None:
    base = {"items": {"task": {"prefix": "TASK", "validators": ["a"]}}}
    override = {"items": {"task": {"prefix": "TSK", "validators": ["z"]}}}
    base_snapshot = {"items": {"task": {"prefix": "TASK", "validators": ["a"]}}}

    deep_merge(base, override, "o")

    assert base == base_snapshot


def test_a_pathologically_deep_untouched_base_subtree_collects_a_violation() -> None:
    """Every failure collects on the same violation channel as everything else — including a
    base subtree the override never touches, nested deep enough to overflow the stack on its
    own, independent of anything the override does. `deep_merge` never raises."""
    base: dict[str, Any] = {"leaf": 1}
    for _ in range(3000):
        base = {"k": base}

    merged, violations = deep_merge(base, {"unrelated": 1}, "o")

    assert merged["unrelated"] == 1
    assert len(violations) == 1
    assert "nesting exceeds" in violations[0].reason


def test_a_pathologically_deep_shared_table_collects_via_deep_merges_own_recursion() -> None:
    """The two tests above both bottom out in `_bounded_deepcopy` (the base-only-key and
    override-only-key branches never actually recurse through `deep_merge` itself). This one
    forces genuine recursive `deep_merge` calls all the way down — base and override share
    every key at every level — so it is the only test exercising `deep_merge`'s own depth
    guard, not `_bounded_deepcopy`'s."""
    base: dict[str, Any] = {"leaf": 1}
    override: dict[str, Any] = {"leaf": 2}
    for _ in range(3000):
        base = {"k": base}
        override = {"k": override}

    _merged, violations = deep_merge(base, override, "o")

    assert len(violations) == 1
    assert "nesting exceeds" in violations[0].reason


def test_a_pathologically_deep_override_branch_does_not_stop_a_sibling_branch_from_merging() -> (
    None
):
    """Collecting rather than raising means the rest of the document still merges: a deep
    branch's violation must not swallow an independent, well-formed sibling key."""
    deep_override: dict[str, Any] = {"leaf": "override-leaf"}
    for _ in range(3000):
        deep_override = {"k": deep_override}
    override = {"deep": deep_override, "shallow": {"prefix": "SH"}}
    base = {"deep": {}, "shallow": {"prefix": "OLD"}}

    merged, violations = deep_merge(base, override, "o")

    assert len(violations) == 1
    assert merged["shallow"]["prefix"] == "SH"


def test_merging_a_real_bundled_spec_field_override_changes_only_that_field() -> None:
    base = _bundled_workflow()
    override = {"statuses": {"Draft": {"role": "attention"}}}

    merged, violations = deep_merge(base, override, "o")

    assert violations == []
    for key, value in base["statuses"]["Draft"].items():
        if key == "role":
            continue
        assert merged["statuses"]["Draft"][key] == value
    assert merged["statuses"]["Draft"]["role"] == "attention"
    # every other status is untouched
    for name, spec in base["statuses"].items():
        if name == "Draft":
            continue
        assert merged["statuses"][name] == spec
