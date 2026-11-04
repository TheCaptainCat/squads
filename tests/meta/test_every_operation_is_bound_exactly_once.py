"""Every operation of the operation table has exactly one handler in the binding tables, and they
bind nothing the operation table does not list; a local-only operation is bound in the local table
and every other one in the service table."""

from collections import Counter

from squads._api import ops
from squads._services import _bindings as services_bindings


def test_every_operation_is_bound_exactly_once() -> None:
    bound_by = (*services_bindings.BINDINGS, *services_bindings.LOCAL_BINDINGS)
    bound = Counter(binding.op.name for binding in bound_by)
    listed = Counter(op.name for op in ops.OPERATIONS)
    assert listed == Counter(set(listed)), (
        f"listed twice in OPERATIONS: {listed - Counter(set(listed))}"
    )
    problems = {name: bound[name] for name in listed if bound[name] != 1}
    strays = sorted(set(bound) - set(listed))
    assert not problems, f"operations not bound exactly once (name: bindings): {problems}"
    assert not strays, f"bound but not in OPERATIONS: {strays}"
    assert all(b.op is next(op for op in ops.OPERATIONS if op.name == b.op.name) for b in bound_by)
    assert all(b.op.local_only for b in services_bindings.LOCAL_BINDINGS)
    assert not any(b.op.local_only for b in services_bindings.BINDINGS)
