"""docs/adoption.md lists every `sq import` op and each field its event model declares."""

import re
from pathlib import Path
from typing import get_args

from squads._services._import_model import ImportEvent, _EventBase

_ADOPTION = Path(__file__).resolve().parents[2] / "docs" / "adoption.md"


def _event_models() -> list[type[_EventBase]]:
    return list(get_args(ImportEvent.__value__))


def _op_of(model: type[_EventBase]) -> str:
    (op,) = get_args(model.model_fields["op"].annotation)
    return op


def _doc_rows() -> dict[str, str]:
    """Map each op in the doc's table to its full row text."""
    rows: dict[str, str] = {}
    for line in _ADOPTION.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*`([a-z-]+)`\s*\|", line)
        if match:
            rows[match.group(1)] = line
    return rows


def test_the_event_models_are_discovered() -> None:
    assert len(_event_models()) > 1


def test_every_op_has_a_row_in_the_import_table() -> None:
    rows = _doc_rows()
    missing = sorted(_op_of(m) for m in _event_models() if _op_of(m) not in rows)
    assert not missing, f"docs/adoption.md import table has no row for: {missing}"


def test_every_declared_field_appears_in_its_ops_row() -> None:
    rows = _doc_rows()
    absent: dict[str, list[str]] = {}
    for model in _event_models():
        row = rows.get(_op_of(model), "")
        names = [f.alias or name for name, f in model.model_fields.items() if name != "op"]
        lost = [n for n in names if f"`{n}`" not in row]
        if lost:
            absent[_op_of(model)] = lost
    assert not absent, f"fields missing from their row in docs/adoption.md: {absent}"
