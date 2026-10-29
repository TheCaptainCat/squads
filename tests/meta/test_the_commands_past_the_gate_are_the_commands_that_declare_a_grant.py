"""The set of operations that get past the schema gate on a mismatched squad is, for each
direction, exactly the set whose declared grant covers that direction. Every operation of the
table is called through the local API on a squad stamped behind and on one stamped ahead, and the
ones the gate does not refuse are collected. A command that makes no call reads only the
package's own data, so the gate has nothing to refuse there."""

import asyncio
import shutil
from pathlib import Path

import pytest

from squads._api._ops import OPERATIONS
from squads._context import RequestContext, bind_context
from squads._errors import SchemaGateError
from squads._services._local_api import LocalApi

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

_PAST_WHEN_BEHIND = {"squad.migrate", "overrides.list", "overrides.diff", "overrides.update"}
_PAST_WHEN_AHEAD: set[str] = set()


def _stamped(tmp_path: Path, direction: str, index: int) -> Path:
    root = shutil.copytree(_CORPUS_DIR / "v0_14", tmp_path / f"squad{index}")
    if direction == "ahead":
        toml = (root / ".squads.toml").read_text(encoding="utf-8")
        (root / ".squads.toml").write_text(
            toml.replace('schema_version = "0.14"', 'schema_version = "0.99"'), encoding="utf-8"
        )
    return root


def _declared(direction: str) -> set[str]:
    return {
        op.name
        for op in OPERATIONS
        if op.grant is not None and op.grant.covers(behind=direction == "behind")
    }


def _observed(direction: str, tmp_path: Path) -> set[str]:
    """The operations the gate lets through. A refused call touches nothing, so the squad is
    copied again only after one that got through."""
    past: set[str] = set()
    root = _stamped(tmp_path, direction, 0)
    for index, op in enumerate(OPERATIONS, start=1):
        bind_context(RequestContext(client_cwd=root))
        try:
            asyncio.run(LocalApi().call(op, op.request.model_construct()))
        except SchemaGateError:
            continue
        except Exception:  # past the gate, a request built without its fields may fail
            pass
        past.add(op.name)
        root = _stamped(tmp_path, direction, index)
    return past


def test_the_walk_sees_the_whole_operation_table() -> None:
    names = {op.name for op in OPERATIONS}
    assert {"items.list", "squad.repair", "check", "squad.migrate", "squad.init"} <= names
    assert len(names) > 100


@pytest.mark.parametrize(
    ("direction", "literal"), [("behind", _PAST_WHEN_BEHIND), ("ahead", _PAST_WHEN_AHEAD)]
)
def test_the_operations_past_the_gate_are_the_ones_that_declare_it(
    direction: str, literal: set[str], tmp_path: Path
) -> None:
    observed = _observed(direction, tmp_path)

    assert observed == _declared(direction)
    assert observed == literal
