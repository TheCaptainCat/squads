"""Repo-hygiene gate: the bundled container-heading table's plural column matches the plural
the bundled spec actually declares for that kind.

``subentity_kinds.<kind>.plural`` is the persisted container-marker name, so it is the thing
the heading sits above: ``## User Stories`` belongs over ``<!-- sq:stories -->``. The three
bundled headings exist only because their wording is not derivable — ``"stories".title()`` is
``"Stories"``, not ``"User Stories"`` — so the table is keyed by kind *and* pinned to the
plural that irregularity belongs to.

Keyed by kind alone, it outranked an adopter's declared plural: renaming story's plural to
``outcomes`` produced a file with ``## User Stories`` written above a container marked
``sq:outcomes``, a bundled default beating a declaration, which is the opposite of what the
method's own docstring promised. The pairing is what fixes that, and this guard is what keeps
the pairing true — a bundled plural changed in ``workflow.toml`` without updating the table
would silently re-open the same gap for every squad, not just an overriding one.
"""

from squads._workflow import bundled_spec
from squads._workflow._models import _BUNDLED_CONTAINER_HEADINGS


def test_every_pinned_heading_names_a_declared_bundled_kind() -> None:
    declared = set(bundled_spec().subentity_kinds)
    unknown = sorted(set(_BUNDLED_CONTAINER_HEADINGS) - declared)
    assert not unknown, (
        f"the heading table pins a kind the bundled spec does not declare: {unknown} — "
        "a renamed or dropped kind must leave the table too, or its entry is dead weight "
        "that can only ever shadow a declared plural"
    )


def test_every_pinned_heading_matches_its_kinds_declared_plural() -> None:
    spec = bundled_spec()
    drifted = {
        kind: (pinned_plural, spec.subentity_kinds[kind].plural)
        for kind, (pinned_plural, _heading) in _BUNDLED_CONTAINER_HEADINGS.items()
        if spec.subentity_kinds[kind].plural != pinned_plural
    }
    assert not drifted, (
        "a bundled kind's declared plural moved without its pinned heading following — the "
        "heading would now render above a container marker of a different name: "
        f"{{kind: (pinned, declared)}} = {drifted}"
    )


def test_a_declared_plural_that_differs_from_the_pinned_one_wins() -> None:
    """The behavioural half. A structural match alone would still pass if the resolution order
    were reversed back, so pin the direction: the declaration outranks the bundled wording."""
    spec = bundled_spec()
    assert spec.subentity_container_heading("story") == "User Stories"

    renamed = spec.model_copy(
        update={
            "subentity_kinds": {
                **spec.subentity_kinds,
                "story": spec.subentity_kinds["story"].model_copy(update={"plural": "outcomes"}),
            }
        }
    )
    assert renamed.subentity_container_heading("story") == "Outcomes"
    assert renamed.subentity_plural("story") == "outcomes"
