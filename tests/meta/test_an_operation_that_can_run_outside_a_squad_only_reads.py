"""An operation composed in the vocabulary mode can run outside any squad, on a service whose
paths name no squad, so it must be a read: its route's method is `GET`."""

from squads._api._api import Mode
from squads._api._ops import OPERATIONS


def test_every_vocabulary_operation_is_a_get() -> None:
    writes = {
        op.name: op.method for op in OPERATIONS if op.mode is Mode.VOCABULARY and op.method != "GET"
    }
    assert not writes, f"an operation that can run outside a squad must be a GET: {writes}"
    assert any(op.mode is Mode.VOCABULARY for op in OPERATIONS)
