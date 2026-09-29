"""``WorkflowSpec.is_delivered`` — "did this status reach its lifecycle's happy-path terminal,
not merely settle some other way" — the bare ``(kind, status)`` comparison a template calls
directly (e.g. ``templates/views/milestone_rollup.md.j2``), with no resolved record needed.
"""

from squads._workflow import bundled_spec
from squads._workflow._models import Lifecycle

SPEC = bundled_spec()


def _kinds_and_machines() -> list[tuple[str, Lifecycle]]:
    item_kinds = [(t, SPEC.machine_for(t)) for t in SPEC.items]
    subentity_kinds = [(k, SPEC.lifecycles[ks.lifecycle]) for k, ks in SPEC.subentity_kinds.items()]
    return item_kinds + subentity_kinds


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


def test_is_delivered_is_true_only_for_the_settled_status_of_every_declared_kind() -> None:
    """Swept over every declared item type and sub-entity kind on the bundled spec — both
    namespaces ``is_delivered`` resolves against: exactly the kind's own
    ``first_settled_status`` is delivered — every other status, settled or not, is not."""
    kinds_and_machines = _kinds_and_machines()
    assert kinds_and_machines, "precondition: the bundled spec declares at least one kind"
    for kind, machine in kinds_and_machines:
        settled_status = SPEC.first_settled_status(kind)
        for status in machine.states:
            assert SPEC.is_delivered(kind, status) == (status == settled_status), (kind, status)
