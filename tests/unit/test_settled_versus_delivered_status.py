"""``WorkflowSpec.is_delivered`` (a bare ``(kind, status)`` pair, for a template with no
resolved record to hand it) pinned against ``squads._views._is_delivered`` (the record-shaped
comparison the untouched ``ref``/``subtree``/``subentity`` projection path still uses) — the
same "did this record reach its lifecycle's happy-path terminal, not merely settle some other
way" question, asked by two call shapes that must never quietly disagree.

Swept over every status of every declared kind on the bundled spec — both namespaces
``is_delivered`` resolves against: item types and sub-entity kinds."""

from squads import _views as views
from squads._workflow import bundled_spec
from squads._workflow._models import Lifecycle

SPEC = bundled_spec()


def _record(kind: str, status: str) -> views._RawRecord:
    return views._RawRecord(
        identity="X-1",
        kind=kind,
        status=status,
        assignee=None,
        title="a record",
        story=None,
        badge_value=lambda _field: None,
    )


def _kinds_and_machines() -> list[tuple[str, Lifecycle]]:
    item_kinds = [(t, SPEC.machine_for(t)) for t in SPEC.items]
    subentity_kinds = [(k, SPEC.lifecycles[ks.lifecycle]) for k, ks in SPEC.subentity_kinds.items()]
    return item_kinds + subentity_kinds


def test_is_delivered_agrees_with_the_record_shaped_comparison_for_every_status_of_every_kind() -> (
    None
):
    kinds_and_machines = _kinds_and_machines()
    assert kinds_and_machines, "precondition: the bundled spec declares at least one kind"
    for kind, machine in kinds_and_machines:
        for status in machine.states:
            record_shaped = views._is_delivered(_record(kind, status), SPEC)
            bare_pair = SPEC.is_delivered(kind, status)
            assert bare_pair == record_shaped, (kind, status)


def test_is_delivered_is_true_for_exactly_the_settled_terminal_not_every_settled_status() -> None:
    """A concrete instance, not just the general sweep: ``task``'s own settled-but-dropped
    exit (``Cancelled``) is settled but not delivered; its happy-path terminal (``Done``) is
    both."""
    dropped = SPEC.first_dropped_status("task")
    settled = SPEC.first_settled_status("task")
    assert dropped is not None
    assert settled is not None
    assert dropped != settled
    assert SPEC.is_delivered("task", dropped) is False
    assert SPEC.is_delivered("task", settled) is True


def test_is_delivered_degrades_to_false_for_an_undeclared_kind_rather_than_raising() -> None:
    assert SPEC.is_delivered("no-such-kind", "Done") is False
