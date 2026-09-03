"""A declared ``ref_rules`` entry is validated and consumed — never a declaration that silently
does nothing.

The seam looked inert. Its own docstring said "not yet consumed by the engine", and a rule for
a kind that does not exist loaded clean and contributed a hint string for a kind every ref
surface rejects: the adopter wrote a rule, nothing refused it, and nothing could ever apply it.
Both halves are pinned here — the kind is validated against the declared ``[ref_kinds]`` set at
load, and each declaration is shown driving the two consumers that read it.

**Not in scope, and deliberately so: which kinds a type may carry.** A declared rule is a rule
*about* a kind, not a permission for one, and reading it as an allowlist would change what the
field means rather than enforce it. Two independent reasons, both checked rather than assumed
(see the two tests at the end of this file). The accepted ``--kind`` vocabulary is declared spec
vocabulary (``WorkflowSpec.ref_kinds``) — a project may declare, rename, or drop a
kind — and the bundled document does not describe an allowlist either: it declares rules on two
types, while the navigational kinds are carried by every type and declared by none.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._loader import _parse_ref_rules


def test_a_rule_naming_a_kind_outside_the_vocabulary_is_refused() -> None:
    declared = frozenset(bundled_spec().ref_kinds)
    with pytest.raises(SquadsError) as excinfo:
        _parse_ref_rules([{"kind": "supersedez"}], "items.decision", declared)
    message = str(excinfo.value)
    assert "supersedez" in message
    assert "supersedes" in message  # the accepted set is named, so the typo is fixable in place


@pytest.mark.parametrize("kind", sorted(bundled_spec().ref_kinds))
def test_every_kind_in_the_vocabulary_is_declarable(kind: str) -> None:
    """The check must be a membership test against the real vocabulary, not a shorter list
    someone typed out beside it."""
    declared = frozenset(bundled_spec().ref_kinds)
    (rule,) = _parse_ref_rules([{"kind": kind, "hint": "h"}], "items.task", declared)
    assert rule.kind == kind


def test_an_unknown_field_in_a_rule_is_still_refused() -> None:
    """The kind check is additional to the model's own strictness, not a replacement for it."""
    declared = frozenset(bundled_spec().ref_kinds)
    with pytest.raises(SquadsError) as excinfo:
        _parse_ref_rules([{"kind": "fixes", "hnit": "typo"}], "items.task", declared)
    assert "hnit" in str(excinfo.value)


def test_a_declared_hint_reaches_the_parent_refusal_message() -> None:
    """First consumer: the hint text is appended to the message an adopter reads when a parent
    is rejected — so a renamed type or a custom rule gets its own wording, not bundled prose."""
    hint = bundled_spec().parent_hint("task")

    declared = {r.hint for r in bundled_spec().item_ref_rules("task") if r.hint}
    assert declared
    assert all(h in hint for h in declared)


def test_a_type_declaring_no_rules_contributes_no_hint() -> None:
    assert bundled_spec().item_ref_rules("epic") == []
    assert "ref add" not in bundled_spec().parent_hint("epic")


def test_the_supersedes_validator_runs_only_for_a_type_that_declares_the_rule() -> None:
    """Second consumer: ``sq check``'s superseded-record warning is gated on the declaration,
    so a project that renames or drops the declaring type takes the check with it rather than
    keeping a bundled type name alive inside the validator."""
    from squads._services._validators import CheckIssue, ValidatorContext, _supersedes_incoming

    spec = bundled_spec()
    assert any(r.kind == "supersedes" for r in spec.item_ref_rules("decision"))
    assert not any(r.kind == "supersedes" for r in spec.item_ref_rules("epic"))

    superseded = next(name for name in spec.statuses if spec.status_role(name) == "superseded")

    def _issues(item_type: str, status: str) -> list[CheckIssue]:
        from datetime import UTC, datetime

        from squads._models._item import Item

        now = datetime(2026, 1, 1, tzinfo=UTC)
        item = Item(
            sequence_id=1,
            type=item_type,
            title="t",
            slug="t",
            status=status,
            path=f"{spec.items[item_type].folder}/x.md",
            created_at=now,
            updated_at=now,
        )
        return _supersedes_incoming(ValidatorContext(item=item, spec=spec))

    assert _issues("decision", superseded)  # declares the rule → checked
    assert _issues("epic", superseded) == []  # declares none → not checked


# --------------------------------------------------------------------- the boundary, checked


def test_the_bundled_document_does_not_describe_an_allowlist() -> None:
    """Why a declared rule cannot be read as "the kinds this type may carry": most of the
    vocabulary is declared by no type at all, so that reading would forbid every navigational
    edge on every type — a change of meaning, not an enforcement of the existing one."""
    spec = bundled_spec()
    declared_anywhere = {r.kind for t in spec.items for r in spec.item_ref_rules(t)}
    all_kinds = frozenset(spec.ref_kinds)

    assert declared_anywhere < all_kinds
    undeclared = all_kinds - declared_anywhere
    assert {"related", "depends-on", "blocks"} <= undeclared


def test_the_accepted_kind_vocabulary_is_read_from_the_spec_not_hardcoded() -> None:
    """The vocabulary is declared workflow-spec data (``[ref_kinds]``), not a fixed set in
    code: a spec that drops a kind refuses a rule naming it, and a spec that declares no rules
    at all still accepts every kind the merged document itself declares."""
    from squads._workflow._loader import _build_spec, _bundled_raw

    raw = _bundled_raw()
    for entry in raw["items"].values():
        entry["ref_rules"] = []
    stripped = _build_spec(raw)

    assert all(stripped.item_ref_rules(t) == [] for t in stripped.items)
    # The ref surfaces are unaffected: the vocabulary they validate against did not move.
    assert "supersedes" in stripped.ref_kinds

    # Dropping a kind from [ref_kinds] makes a rule naming it refuse to load.
    raw = _bundled_raw()
    del raw["ref_kinds"]["supersedes"]
    with pytest.raises(SquadsError, match="supersedes"):
        _build_spec(raw)
