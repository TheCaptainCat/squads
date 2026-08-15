"""The public entry point: check the override's own top level, resolve splats against the
base, deep-merge, apply `selected`, strip it, in that fixed order — with fail-fast and
collect-all calling modes over one shared code path."""

import importlib.resources
import tomllib
from typing import Any

import pytest

from _helpers import SPECMERGE_WORKFLOW_SECTIONS as WORKFLOW_SECTIONS
from squads._errors import SquadsError
from squads._specmerge import merge_override


def _bundled_playbook() -> dict[str, Any]:
    pkg = importlib.resources.files("squads._specs")
    raw: dict[str, Any] = tomllib.loads((pkg / "playbook.toml").read_bytes().decode())
    return raw


def _bundled_workflow() -> dict[str, Any]:
    pkg = importlib.resources.files("squads._specs")
    raw: dict[str, Any] = tomllib.loads((pkg / "workflow.toml").read_bytes().decode())
    return raw


def test_the_three_mechanisms_run_in_order_splat_then_merge_then_selected() -> None:
    base = {
        "items": {"epic": {"prefix": "EPIC"}, "guide": {"prefix": "GDE"}},
        "widgets": {"colors": ["red"]},
    }
    override = {
        "widgets": {"colors": ["$(*self)", "blue"]},
        "items": {"epic": {"prefix": "EP"}},
        "selected": {"items": ["epic"]},
    }

    result = merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=None)

    assert result.violations == ()
    assert result.merged is not None
    # splat resolved before merge:
    assert result.merged["widgets"]["colors"] == ["red", "blue"]
    # merge happened (field shadowed, siblings survive would-be selected drop until applied):
    assert result.merged["items"]["epic"]["prefix"] == "EP"
    # selected applied after merge, and stripped — order pinned, not just membership:
    assert list(result.merged["items"]) == ["epic"]
    assert "selected" not in result.merged


def test_an_empty_override_is_a_no_op() -> None:
    base: dict[str, Any] = {
        "items": {"epic": {"prefix": "EPIC"}, "task": {"prefix": "TASK"}},
        "z": 9,
    }

    result = merge_override(base, {}, WORKFLOW_SECTIONS, "o", top_level_keys=None)

    assert result.violations == ()
    assert result.merged == base
    # "same nesting, nothing added and nothing stripped" includes key order, which `==` alone
    # is blind to:
    assert result.merged is not None
    assert list(result.merged) == list(base)
    assert list(result.merged["items"]) == list(base["items"])


def test_the_merged_result_shares_no_structure_with_either_input_through_the_entry_point() -> None:
    """Independence is stated at the `merge_override` boundary too, not just inside
    `deep_merge` — including an untouched base list, a `$(path)`-spliced table, and a
    `$(*path)`-spread list, the three places a missed copy could hide."""
    base: dict[str, Any] = {
        "items": {"task": {"validators": ["a"]}},
        "shared_table": {"x": 1},
        "shared_list": ["p", "q"],
    }
    override: dict[str, Any] = {
        "items": {"epic": {"spliced": "$(shared_table)"}},
        "shared_list_copy": ["$(*shared_list)", "r"],
    }

    result = merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=None)

    assert result.violations == ()
    assert result.merged is not None
    assert result.merged["items"]["task"] is not base["items"]["task"]  # untouched base table
    assert result.merged["items"]["task"]["validators"] is not base["items"]["task"]["validators"]
    assert result.merged["items"]["epic"]["spliced"] is not base["shared_table"]  # spliced table

    result.merged["items"]["task"]["validators"].append("mutated")
    result.merged["items"]["epic"]["spliced"]["x"] = "mutated"
    result.merged["shared_list_copy"].append("mutated")
    assert base["items"]["task"]["validators"] == ["a"]
    assert base["shared_table"] == {"x": 1}
    assert base["shared_list"] == ["p", "q"]


def test_two_overrides_of_unrelated_keys_produce_equal_merged_mappings_in_either_order() -> None:
    """Splat resolution targets the base only, so the merge is order-independent — exercised
    over a base that includes a splat target, where the property could actually break."""
    base = {
        "items": {"epic": {"prefix": "EPIC"}, "task": {"prefix": "TASK"}},
        "widgets": {"colors": ["red", "green"]},
    }
    override_ab = {
        "items": {"epic": {"prefix": "EP"}},
        "widgets": {"colors": ["$(*self)", "blue"]},
    }
    override_ba = {
        "widgets": {"colors": ["$(*self)", "blue"]},
        "items": {"epic": {"prefix": "EP"}},
    }

    result_ab = merge_override(base, override_ab, WORKFLOW_SECTIONS, "o", top_level_keys=None)
    result_ba = merge_override(base, override_ba, WORKFLOW_SECTIONS, "o", top_level_keys=None)

    assert result_ab.violations == result_ba.violations == ()
    assert result_ab.merged == result_ba.merged


def test_fail_fast_mode_raises_a_squads_error_on_the_first_violation() -> None:
    base = {"widgets": {"colors": ["red"]}}
    override = {"widgets": {"colors": ["$(*no.such.path)"]}}

    with pytest.raises(SquadsError):
        merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=None)


def test_fail_fast_raises_the_first_violation_not_merely_any_violation() -> None:
    """A document with exactly one violation cannot distinguish "the first" from "any" — this
    one carries two independent violations from the *same* mechanism (so picking the wrong
    end of the list, not just the wrong mechanism, would be caught), and the raised message
    must name the specific one that comes first in document order, plus carry the origin
    label and dotted path every raise is required to carry."""
    base = {"widgets": {"colors": ["red"]}}
    override = {"widgets": {"colors": ["$(*missing.one)"], "sizes": ["$(*missing.two)"]}}

    with pytest.raises(SquadsError) as excinfo:
        merge_override(
            base,
            override,
            WORKFLOW_SECTIONS,
            "override.toml",
            collect_all=False,
            top_level_keys=None,
        )

    message = str(excinfo.value)
    assert "override.toml" in message
    assert "widgets.colors" in message
    assert "widgets.sizes" not in message


def test_fail_fast_raises_the_first_cross_mechanism_violation() -> None:
    """A resolution violation and a `selected` violation together: resolution runs first
    unconditionally, so its violation wins regardless of which key the override declares
    first — see the next test for the reorder check."""
    base = {"widgets": {"colors": ["red"]}}
    override = {
        "widgets": {"colors": ["$(*missing.one)"]},
        "selected": {"bogus-section": ["x"]},
    }

    with pytest.raises(SquadsError) as excinfo:
        merge_override(
            base,
            override,
            WORKFLOW_SECTIONS,
            "override.toml",
            collect_all=False,
            top_level_keys=None,
        )

    message = str(excinfo.value)
    assert "override.toml" in message
    assert "widgets.colors" in message
    assert "bogus-section" not in message


def test_fail_fast_first_violation_is_deterministic_across_override_key_order() -> None:
    """The same document, with its top-level keys declared in reversed order, must raise the
    same violation: first-violation identity is fixed **mechanism order, then document
    order** — resolution runs before `selected` unconditionally, so a resolution violation
    always wins over a `selected` violation no matter which key the override declares first.
    (Two violations from the *same* mechanism are not claimed to be order-independent — only
    cross-mechanism ordering is a stated guarantee.)"""
    base = {"widgets": {"colors": ["red"]}}
    forward = {
        "widgets": {"colors": ["$(*missing.one)"]},
        "selected": {"bogus-section": ["x"]},
    }
    reversed_override = {
        "selected": {"bogus-section": ["x"]},
        "widgets": {"colors": ["$(*missing.one)"]},
    }

    with pytest.raises(SquadsError) as forward_excinfo:
        merge_override(base, forward, WORKFLOW_SECTIONS, "o", top_level_keys=None)
    with pytest.raises(SquadsError) as reversed_excinfo:
        merge_override(base, reversed_override, WORKFLOW_SECTIONS, "o", top_level_keys=None)

    assert str(forward_excinfo.value) == str(reversed_excinfo.value)


def test_fail_fast_is_the_default_calling_mode() -> None:
    base = {"widgets": {}}
    override = {"selected": {"widgets": ["x"]}}

    with pytest.raises(SquadsError):
        merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=None)


def test_collect_all_mode_reports_every_independent_violation_together() -> None:
    base = {"widgets": {"colors": ["red"]}}
    override = {
        # a malformed, unclosed token — in territory, not a well-formed token:
        "widgets": {"colors": ["$(*missing.path)"], "note": "$(oops"},
        "selected": {"bogus-section": ["x"]},
    }

    result = merge_override(
        base, override, WORKFLOW_SECTIONS, "o", collect_all=True, top_level_keys=None
    )

    assert result.merged is None
    assert len(result.violations) == 3


def test_collect_all_mode_does_not_stop_at_the_first_violation() -> None:
    base = {"widgets": {}}
    override = {"selected": {"bogus-one": ["x"], "bogus-two": ["y"]}}

    result = merge_override(
        base, override, WORKFLOW_SECTIONS, "o", collect_all=True, top_level_keys=None
    )

    reported = {v.path for v in result.violations}
    assert reported == {"selected.bogus-one", "selected.bogus-two"}
    # a merge that failed closed has nothing usable to hand back — pinned for a `selected`
    # shape violation specifically, not just for a resolution violation as elsewhere in this
    # file.
    assert result.merged is None


def test_a_pathologically_deep_base_collects_through_the_full_entry_point() -> None:
    """The nesting refusal is on the same collected channel as every other violation, all the
    way up through `merge_override` — not just inside `deep_merge` itself. In collect-all
    mode it must never raise; in fail-fast mode it still does, via the same `_maybe_raise`
    path as everything else."""
    deep: dict[str, Any] = {"leaf": 1}
    deep_override: dict[str, Any] = {"leaf": 2}
    for _ in range(3000):
        deep = {"k": deep}
        deep_override = {"k": deep_override}
    base: dict[str, Any] = {"deep": deep, "shallow": {"prefix": "OLD"}}
    override: dict[str, Any] = {"deep": deep_override, "shallow": {"prefix": "NEW"}}

    result = merge_override(
        base, override, WORKFLOW_SECTIONS, "o", collect_all=True, top_level_keys=None
    )

    assert result.merged is None
    # both walks guard independently — resolve_splat_refs hits the bound walking the deeply
    # nested override, and deep_merge hits it again walking the same structure — so this is
    # genuinely two violations, not one; collect-all reports both rather than stopping.
    assert len(result.violations) == 2
    assert all("nesting exceeds" in v.reason for v in result.violations)

    with pytest.raises(SquadsError):
        merge_override(
            base, override, WORKFLOW_SECTIONS, "o", collect_all=False, top_level_keys=None
        )


def test_a_clean_override_never_raises_in_either_mode() -> None:
    base = {"widgets": {"colors": ["red"]}}
    override = {"widgets": {"colors": ["$(*self)", "blue"]}}

    fail_fast = merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=None)
    collect_all = merge_override(
        base, override, WORKFLOW_SECTIONS, "o", collect_all=True, top_level_keys=None
    )

    assert fail_fast.merged == collect_all.merged
    assert fail_fast.merged is not None
    assert fail_fast.merged["widgets"]["colors"] == ["red", "blue"]


def test_a_dangling_splat_path_is_never_reordered_past_a_selected_violation() -> None:
    """Nothing later in the pipeline may run ahead of splat resolution: a resolution
    violation is collected (and, in fail-fast mode, raised) without ever reaching the merge
    or the deselect step."""
    base = {"widgets": {}}
    override = {"widgets": {"colors": ["$(*missing)"]}}

    result = merge_override(
        base, override, WORKFLOW_SECTIONS, "o", collect_all=True, top_level_keys=None
    )

    assert len(result.violations) == 1
    assert "dangling" in result.violations[0].reason


def test_array_of_tables_splat_append_end_to_end_against_the_real_bundled_playbook() -> None:
    base = _bundled_playbook()
    override_source = """
    [types.feature]
    roles = ["$(*self)", { slug = "custom-role", enter = ["do the custom thing"] }]
    """
    override = tomllib.loads(override_source)

    result = merge_override(
        base, override, frozenset({"types"}), "playbook-override.toml", top_level_keys=None
    )

    assert result.violations == ()
    assert result.merged is not None
    feature_roles = result.merged["types"]["feature"]["roles"]
    assert feature_roles[:-1] == base["types"]["feature"]["roles"]
    assert feature_roles[-1]["slug"] == "custom-role"
    # every other type is untouched
    for name, spec in base["types"].items():
        if name == "feature":
            continue
        assert result.merged["types"][name] == spec


# ---------------------------------------------------------------------- closed top-level keys
# The override document's own top level, as a closed key space when the caller supplies one —
# checked before the merge, the only point at which the override's own top level is still
# distinguishable from the base's. Fixes a live fail-open: a mistyped section name silently
# does nothing against the real loader today, because each loader hand-builds its spec model
# from an explicit payload of named sections and `extra="forbid"` never sees the stray key.


def test_a_mistyped_top_level_section_name_fails_closed_naming_the_key_and_accepted_set() -> None:
    """The case that matters: `[item.task]` for `[items.task]` — not the retired stamp key —
    where the adopter's entire override would otherwise silently do nothing against a spec
    that is perfectly valid and simply not the one they wrote."""
    base = {"items": {"task": {"prefix": "TASK"}}}
    override = {"item": {"task": {"prefix": "TSK"}}}

    result = merge_override(
        base,
        override,
        WORKFLOW_SECTIONS,
        "override.toml",
        collect_all=True,
        top_level_keys=WORKFLOW_SECTIONS,
    )

    assert result.merged is None
    assert len(result.violations) == 1
    assert "item" in result.violations[0].reason
    for name in sorted(WORKFLOW_SECTIONS):
        assert name in result.violations[0].hint


def test_a_mistyped_top_level_section_name_does_not_merge_clean() -> None:
    """Driven the way the real defect was found: an override naming only a mistyped section
    must not produce a merged mapping equal to the unmodified base — today it does, because
    the stray key is silently dropped before the model ever sees it."""
    base = {"items": {"task": {"prefix": "TASK"}}}
    override = {"item": {"task": {"prefix": "TSK"}}}

    with pytest.raises(SquadsError):
        merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=WORKFLOW_SECTIONS)


def test_a_retired_override_base_key_at_the_top_level_fails_closed() -> None:
    base = {"items": {"task": {"prefix": "TASK"}}}
    override = {"override_base": "0.13.0"}

    result = merge_override(
        base,
        override,
        WORKFLOW_SECTIONS,
        "o",
        collect_all=True,
        top_level_keys=WORKFLOW_SECTIONS,
    )

    assert result.merged is None
    assert len(result.violations) == 1
    assert "override_base" in result.violations[0].reason


def test_called_with_no_accepted_top_level_set_every_top_level_key_passes_through() -> None:
    """The roles loader is this caller: a role override's top-level keys are the fields of a
    role, a set that grows release to release, so leniency there is forward compatibility,
    not a gap. Omitting `top_level_keys` gets no check at all."""
    base = {"items": {"task": {"prefix": "TASK"}}}
    override = {"totally_bogus_key": {"whatever": True}}

    result = merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=None)

    assert result.violations == ()
    assert result.merged is not None
    assert result.merged["totally_bogus_key"] == {"whatever": True}


def test_the_top_level_check_runs_before_splat_resolution() -> None:
    """Ordering: the top-level check goes first, before splat resolution even runs, because
    it is the only point at which the override's own top level is still distinguishable from
    the base's. A document carrying both an unknown top-level key and a splat violation must
    raise the top-level one first in fail-fast mode."""
    base = {"items": {}}
    override = {"bogus": {"x": "$(*missing)"}}

    with pytest.raises(SquadsError) as excinfo:
        merge_override(base, override, WORKFLOW_SECTIONS, "o", top_level_keys=frozenset({"items"}))

    assert "bogus" in str(excinfo.value)
    assert "missing" not in str(excinfo.value)


def test_the_top_level_violation_collects_beside_other_violations_in_collect_all_mode() -> None:
    base = {"items": {}}
    override = {"bogus": {"x": "$(*missing)"}}

    result = merge_override(
        base,
        override,
        WORKFLOW_SECTIONS,
        "o",
        collect_all=True,
        top_level_keys=frozenset({"items"}),
    )

    assert result.merged is None
    assert len(result.violations) == 2
    reasons = " ".join(v.reason for v in result.violations)
    assert "bogus" in reasons
    assert "missing" in reasons


def test_a_recognised_top_level_key_set_merges_clean() -> None:
    base = {"items": {"task": {"prefix": "TASK"}}}
    override = {"items": {"task": {"prefix": "TSK"}}, "selected": {"items": ["task"]}}

    result = merge_override(
        base,
        override,
        WORKFLOW_SECTIONS,
        "o",
        top_level_keys=WORKFLOW_SECTIONS | {"selected"},
    )

    assert result.violations == ()
    assert result.merged is not None
    assert result.merged["items"]["task"]["prefix"] == "TSK"


def test_selected_at_the_top_level_is_accepted_even_when_the_callers_set_omits_it() -> None:
    """`selected` is the engine's own reserved key, not the document's vocabulary — a caller
    should never have to know to add it to their accepted set. This is the natural
    derivation a loader reaches for (the document's own section names, nothing more) and it
    must not refuse a legitimate override for a document the adopter got right."""
    base = {"items": {"task": {"prefix": "TASK"}, "epic": {"prefix": "EPIC"}}}
    override = {"selected": {"items": ["task"]}}

    result = merge_override(
        base,
        override,
        WORKFLOW_SECTIONS,
        "o",
        top_level_keys=WORKFLOW_SECTIONS,  # deliberately NOT including "selected"
    )

    assert result.violations == ()
    assert result.merged is not None
    assert list(result.merged["items"]) == ["task"]


def test_selected_at_the_top_level_is_accepted_against_the_real_bundled_workflow_spec() -> None:
    """Driven exactly as the defect was found: the caller's set is every workflow document
    key or the six section names — both the derivations a real loader is most likely to
    reach for — with `selected` deliberately absent from both."""
    base = _bundled_workflow()
    six_sections = frozenset(
        {"items", "statuses", "lifecycles", "collections", "subentity_kinds", "roles"}
    )
    override = {"selected": {"items": ["task"]}}

    for top_level_keys in (frozenset(base.keys()), six_sections):
        result = merge_override(base, override, six_sections, "o", top_level_keys=top_level_keys)
        assert result.violations == ()
        assert result.merged is not None
