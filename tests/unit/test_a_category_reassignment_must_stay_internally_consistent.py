"""A category reassignment is validated for internal consistency at load, and hard-stops.

An override may move a built-in between `work` and `records` — that is settled, and the
guardrail is stated as validation rather than prohibition. What was never checked is whether the
*result* is coherent, and the failure was silent on every gate: `sq list` exit 0,
`sq workflow lint` "workflow spec OK — no errors or warnings", `sq check` exit 0. Moving `task`
to `records` while it still declared `parents` and `parent_required` made that constraint
unreachable in both directions — creating with no parent succeeded where a parent had been
*required*, and creating with the declared parent was refused by the records rule — while the
loaded spec went on reporting both fields.

The check is written against the effective **validator set**, not against the category name,
because the validator set is what a category actually is: nothing else in the engine branches on
`work` versus `records` (every other category consumer asks only "roster or not"). Two
consequences the tests below pin: it catches a type that adds `no_parent` to its own
`validators` while declaring `parents`, with no reassignment involved at all; and a reassignment
that silences nothing still loads, because permitting the move is the point.

Being defined over the validator set also fixes what "complete" means: one clause per validator
whose subject is a declared capability. The coverage test at the bottom pins that closure
against the whole closed catalog, so the next validator added to a bundle cannot quietly arrive
without one — a clause set written against the fields that came to mind instead is exactly how
`supersedes_incoming` (a `records`-only validator gated on a declared `supersedes` ref rule) and
`subtask_story_mapping` (a `work`-only validator gated on the hosted kind's `maps_parent_story`)
were left unguarded when the first two clauses landed.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow._loader import _build_spec, _bundled_raw
from squads._workflow._models import (
    CATEGORY_BUNDLES,
    COMMON_CORE,
    CONSISTENCY_CLAUSES,
    SUBENTITY_VALIDATOR_NAMES,
    UNGUARDED_VALIDATOR_NAMES,
    VALIDATOR_NAMES,
)


def _spec_with(overrides: dict[str, dict[str, object]]):
    """Build a spec from the bundled document with per-type fields replaced — the same raw
    mapping an override merge produces, so these exercise the real load path."""
    raw = _bundled_raw()
    for type_name, fields in overrides.items():
        raw["items"][type_name] = {**raw["items"][type_name], **fields}
    return _build_spec(raw)


# --------------------------------------------------------------- must now refuse

#: (id, per-type override, the substring the refusal must carry). Every entry leaves a
#: declaration the type's own validator set can never act on.
_INCONSISTENT: list[tuple[str, dict[str, dict[str, object]], str]] = [
    (
        "task_to_records_keeps_parents_and_parent_required",
        {"task": {"category": "records"}},
        "parent_required='feature'",
    ),
    (
        "feature_to_records_keeps_parents",
        {"feature": {"category": "records"}},
        "parents=['epic']",
    ),
    (
        "review_to_records_still_hosts_findings",
        {"review": {"category": "records"}},
        "subentity_kind 'finding'",
    ),
    (
        "feature_to_records_still_hosts_stories",
        {"feature": {"category": "records"}},
        "subentity_kind 'story'",
    ),
    (
        "records_type_declaring_parent_required_only",
        {"bug": {"category": "records", "parent_required": "epic"}},
        "parent_required='epic'",
    ),
    (
        "records_type_declaring_parents_only",
        {"bug": {"category": "records", "parents": ["epic"]}},
        "parents=['epic']",
    ),
    (
        "work_type_adding_no_parent_while_declaring_parents",
        {"feature": {"validators": ["no_parent"]}},
        "parents=['epic']",
    ),
    (
        "custom_records_type_hosting_a_kind",
        {"guide": {"subentity_kind": "story"}},
        "subentity_kind 'story'",
    ),
    # `supersedes_incoming` lives in the `records` bundle and nowhere else, and returns early
    # unless the type declares a `supersedes` ref rule — the same shape the parent clause
    # refuses, and the reason a reassignment that keeps the rule keeps a dead declaration.
    (
        "decision_to_work_keeps_its_supersedes_rule",
        {"decision": {"category": "work"}},
        "'supersedes' ref rule",
    ),
    (
        "records_type_given_a_supersedes_rule_under_work",
        {"bug": {"ref_rules": [{"kind": "supersedes", "hint": ""}]}},
        "'supersedes' ref rule",
    ),
    # `subtask_story_mapping` is gated on the hosted KIND's maps_parent_story, so satisfying
    # the sub-entity clause by naming one check back does not cover it.
    (
        "task_to_records_named_back_still_loses_the_story_mapping",
        {
            "task": {
                "category": "records",
                "parents": [],
                "parent_required": None,
                "validators": ["subentity_status_valid"],
            }
        },
        "maps_parent_story",
    ),
    # The `roster` bundle is empty, so a parents allowlist under it is read by nothing — the
    # unenforced arm, distinct from the no_parent contradiction above.
    (
        "roster_type_declaring_parents_has_nothing_reading_them",
        {"role": {"parents": ["epic"]}},
        "no validator that reads it ('parent_in')",
    ),
    # Contradictions between two declarations rather than between a declaration and a bundle.
    # `parent_required` names the single type the story mapping resolves its host through; a
    # `parents` allowlist that excludes it makes that host the one parent `parent_in` refuses,
    # so the mapping is dead in both directions while the spec reports both fields.
    (
        "parent_required_naming_a_type_the_parents_allowlist_excludes",
        {"task": {"parents": ["epic"]}},
        "allowlist excludes that type",
    ),
    # `parent_present` demands a parent and `no_parent` forbids one. Reachable two ways, and
    # both are covered: naming both on one type, and naming the mandatory half on a type whose
    # category already supplies the forbidding half.
    (
        "one_type_naming_both_the_mandatory_and_the_forbidden_parent_check",
        {"epic": {"validators": ["no_parent", "parent_present"]}},
        "refused however it is created",
    ),
    (
        "records_type_naming_the_mandatory_parent_check_its_bundle_forbids",
        {"bug": {"category": "records", "validators": ["parent_present"]}},
        "refused however it is created",
    ),
]


@pytest.mark.parametrize(
    ("case", "overrides", "expected"), _INCONSISTENT, ids=[c for c, _, _ in _INCONSISTENT]
)
def test_an_inconsistent_reassignment_fails_closed_at_load(case, overrides, expected) -> None:
    with pytest.raises(SquadsError) as excinfo:
        _spec_with(overrides)
    message = str(excinfo.value)
    assert expected in message, message


def test_the_refusal_names_the_type_the_category_and_a_way_out() -> None:
    """A load-time hard stop that does not say what to change is a worse defect than the silent
    wrong answer it replaces — the adopter cannot even reach a diagnostic without fixing it."""
    with pytest.raises(SquadsError) as excinfo:
        _spec_with({"task": {"category": "records"}})
    message = str(excinfo.value)

    assert "'task'" in message  # which type
    assert "'records'" in message  # which category
    assert "no_parent" in message  # why: the validator its category turns on
    assert "Drop the parent field(s)" in message  # what to change
    assert "category that allows a parent" in message  # …or the other way out


# --------------------------------------------------------------- must still load


#: Reassignment is permitted; only an inconsistent one is refused. These are the control, and
#: they carry more weight than the refusals: a check that simply forbade reassignment would pass
#: every test above.
_CONSISTENT: list[tuple[str, dict[str, dict[str, object]]]] = [
    ("bug_to_records", {"bug": {"category": "records"}}),
    (
        "decision_to_work_dropping_the_rule_it_would_silence",
        {"decision": {"category": "work", "ref_rules": []}},
    ),
    (
        "decision_to_work_naming_the_supersedes_check_back",
        {"decision": {"category": "work", "validators": ["supersedes_incoming"]}},
    ),
    ("guide_to_work", {"guide": {"category": "work"}}),
    (
        "task_to_records_dropping_what_records_forbids",
        {
            "task": {
                "category": "records",
                "parents": [],
                "parent_required": None,
                "subentity_kind": None,
            }
        },
    ),
    # Opting a type into the mandatory-parent check is the supported way to make
    # `parent_required` read the way its name does. It must load, or the opt-in is not one.
    ("task_opting_into_a_mandatory_parent", {"task": {"validators": ["parent_present"]}}),
    # An empty `parents` is "any parent", so it excludes nothing and no allowlist contradiction
    # exists — the control that keeps the new arm from firing on a correct spec.
    (
        "parent_required_under_an_allowlist_that_admits_anything",
        {"bug": {"parent_required": "epic"}},
    ),
]


@pytest.mark.parametrize("case,overrides", _CONSISTENT, ids=[c for c, _ in _CONSISTENT])
def test_a_consistent_reassignment_still_loads(case, overrides) -> None:
    spec = _spec_with(overrides)
    (type_name,) = overrides
    assert type_name in spec.items


def test_the_bundled_spec_is_itself_consistent() -> None:
    """The floor under everything: the check must not refuse the document squads ships."""
    assert _build_spec(_bundled_raw()).items


def test_a_record_may_host_sub_entities_by_naming_the_checks_it_wants_back() -> None:
    """This is what keeps the sub-entity clause validation rather than prohibition. The
    `validators` list is extend-only from the closed catalog, so an adopter who genuinely wants
    a record that hosts sub-entities has a way to say so — and the refusal names it."""
    spec = _spec_with(
        {
            "review": {
                "category": "records",
                "validators": sorted(SUBENTITY_VALIDATOR_NAMES),
            }
        }
    )
    assert spec.items["review"].category == "records"
    assert spec.items["review"].subentity_kind == "finding"


def test_naming_only_one_of_the_sub_entity_checks_is_enough_to_be_coherent() -> None:
    """ "At least one", not "all four": the clause exists because a declared kind would otherwise
    have *nothing* watching it, and one named check is a deliberate, readable choice."""
    spec = _spec_with({"review": {"category": "records", "validators": ["subentity_status_valid"]}})
    assert spec.items["review"].category == "records"


# --------------------------------------------------------------- the constant stays honest


def test_every_sub_entity_validator_name_is_a_real_catalog_member() -> None:
    assert SUBENTITY_VALIDATOR_NAMES <= VALIDATOR_NAMES


def test_the_work_bundle_supplies_every_sub_entity_validator_the_clause_looks_for() -> None:
    """If the two ever drift, a `work` type hosting a kind would refuse its own bundled spec —
    so this pins the relationship the clause depends on rather than trusting two lists."""
    assert set(CATEGORY_BUNDLES["work"]) >= SUBENTITY_VALIDATOR_NAMES
    assert not (set(CATEGORY_BUNDLES["records"]) & SUBENTITY_VALIDATOR_NAMES)


# --------------------------------------------------------------- the clause set stays closed


def _guarded() -> frozenset[str]:
    return frozenset(name for names, _ in CONSISTENCY_CLAUSES for name in names)


def test_every_validator_is_guarded_common_core_or_argued_unguarded() -> None:
    """The completeness property, and the whole reason the clauses are a registry: the rule is
    defined over the validator set, so "is it complete?" is answerable only per validator. A
    catalog member that is neither guarded by a clause, nor unconditionally effective, nor
    named as deliberately unguarded is a capability whose enforcement a category can switch off
    with no report — which is the defect this check exists to prevent, one level up.
    """
    classified = _guarded() | frozenset(COMMON_CORE) | UNGUARDED_VALIDATOR_NAMES
    assert classified == VALIDATOR_NAMES, sorted(VALIDATOR_NAMES - classified)


def test_no_validator_is_classified_twice() -> None:
    """Overlap would make the coverage assertion above satisfiable by accident — a name
    "covered" as unguarded while a clause also claims it hides which statement is load-bearing.
    """
    buckets = [_guarded(), frozenset(COMMON_CORE), UNGUARDED_VALIDATOR_NAMES]
    assert sum(len(b) for b in buckets) == len({name for b in buckets for name in b})


def test_a_guarded_name_is_never_unconditionally_effective() -> None:
    """A clause guards reachability, so it is only meaningful for a validator some category can
    leave out. One that ships in every effective set has nothing to guard."""
    assert not (_guarded() & frozenset(COMMON_CORE))


def test_every_guarded_name_belongs_to_some_category_bundle() -> None:
    """The converse pin: a clause naming a validator no bundle supplies would refuse every type
    that declares its subject, with no category able to satisfy it."""
    bundled = frozenset(name for names in CATEGORY_BUNDLES.values() for name in names)
    assert _guarded() <= bundled
