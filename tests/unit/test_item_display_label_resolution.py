"""``label_for`` — the per-type display-label resolver: pin-else-derive across all
four independent forms (``singular``/``plural``/``singular_lower``/``plural_lower``), a regular
type needing zero config, a partial override pinning only some forms, and an acronym type
pinning every form so its ``*_lower`` forms stay capitalized rather than getting corrupted by
naive lowercasing.
"""

from typing import ClassVar

import pytest
from pydantic import ValidationError

from squads._models._vocab import label_for, labels_for
from squads._workflow._models import ItemSpec, LabelSpec


def _spec_with(type_str: str, item_spec: ItemSpec) -> object:
    """A minimal duck-typed stand-in for ``WorkflowSpec`` — ``label_for`` only ever reads
    ``.items[type_str].labels`` off it, so a bare namespace is enough and keeps these tests
    decoupled from constructing a full ``WorkflowSpec``."""

    class _Spec:
        items: ClassVar[dict[str, ItemSpec]] = {type_str: item_spec}

    return _Spec()


# --------------------------------------------------------------------------- pin-else-derive


def test_a_regular_type_with_no_labels_table_derives_all_four_forms() -> None:
    item_spec = ItemSpec(prefix="TST", folder="tests", lifecycle="work")
    spec = _spec_with("story", item_spec)
    assert labels_for("story", spec) == {
        "singular": "Story",
        "singular_lower": "story",
        "plural": "Storys",  # naive derivation — exactly why irregular plurals get pinned
        "plural_lower": "storys",
    }


def test_no_spec_at_all_still_derives_every_form() -> None:
    assert label_for("task", "singular") == "Task"
    assert label_for("task", "plural_lower") == "tasks"


def test_an_undeclared_type_falls_back_to_derivation_rather_than_raising() -> None:
    item_spec = ItemSpec(prefix="TST", folder="tests", lifecycle="work")
    spec = _spec_with("story", item_spec)  # spec declares "story", not "widget"
    assert label_for("widget", "singular", spec) == "Widget"


def test_a_partial_override_pins_the_declared_forms_and_derives_the_rest() -> None:
    item_spec = ItemSpec(
        prefix="BUG",
        folder="bugs",
        lifecycle="work",
        labels=LabelSpec(plural="Defects"),
    )
    spec = _spec_with("bug", item_spec)
    resolved = labels_for("bug", spec)
    assert resolved["plural"] == "Defects"  # pinned
    assert resolved["singular"] == "Bug"  # derived
    assert resolved["singular_lower"] == "bug"  # derived
    assert resolved["plural_lower"] == "bugs"  # derived


def test_a_form_pinned_to_the_empty_string_falls_back_to_the_computed_form() -> None:
    item_spec = ItemSpec(
        prefix="BUG",
        folder="bugs",
        lifecycle="work",
        labels=LabelSpec(singular=""),
    )
    spec = _spec_with("bug", item_spec)
    assert label_for("bug", "singular", spec) == "Bug"  # "" is not "present", so derive


def test_an_acronym_type_with_every_form_pinned_keeps_its_lower_forms_capitalized() -> None:
    item_spec = ItemSpec(
        prefix="ADR",
        folder="adrs",
        lifecycle="adr",
        labels=LabelSpec(
            singular="ADR",
            plural="ADRs",
            singular_lower="ADR",
            plural_lower="ADRs",
        ),
    )
    spec = _spec_with("adr", item_spec)
    resolved = labels_for("adr", spec)
    assert resolved == {
        "singular": "ADR",
        "plural": "ADRs",
        "singular_lower": "ADR",  # stays capitalized — not "adr"
        "plural_lower": "ADRs",  # stays capitalized — not "adrs"
    }


# --------------------------------------------------------------------------- schema


def test_label_spec_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        LabelSpec.model_validate({"singular": "Thing", "plurals": "Things"})  # misspelled


def test_item_spec_labels_defaults_to_none() -> None:
    assert ItemSpec(prefix="TST", folder="tests", lifecycle="work").labels is None
