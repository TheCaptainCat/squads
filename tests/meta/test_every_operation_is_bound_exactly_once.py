"""Every operation of the operation table has exactly one handler in the binding table, and the
binding table binds nothing the operation table does not list."""

from collections import Counter

from squads._api._ops import OPERATIONS
from squads._services._bindings import BINDINGS


def test_every_operation_is_bound_exactly_once() -> None:
    bound = Counter(binding.op.name for binding in BINDINGS)
    listed = Counter(op.name for op in OPERATIONS)
    assert listed == Counter(set(listed)), (
        f"listed twice in OPERATIONS: {listed - Counter(set(listed))}"
    )
    problems = {name: bound[name] for name in listed if bound[name] != 1}
    strays = sorted(set(bound) - set(listed))
    assert not problems, f"operations not bound exactly once (name: bindings): {problems}"
    assert not strays, f"bound but not in OPERATIONS: {strays}"
    assert all(b.op is next(op for op in OPERATIONS if op.name == b.op.name) for b in BINDINGS)
