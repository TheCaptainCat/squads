"""The create/update gate evaluates a catalog member only when its resolved level for the item's
type is ``error`` (and its declared context is held); ``report()`` evaluates every effective
member at every level. Driven over the whole catalog with each member's function wrapped to
count calls, so a member added later is covered by the same table.
"""

from datetime import UTC, datetime

import pytest

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX
from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._services._results import CheckIssue
from squads._services._validators import (
    CATALOG,
    VALIDATOR_CONTEXT,
    Validator,
    ValidatorContext,
    ValidatorEngine,
)
from squads._workflow import bundled_spec
from squads._workflow._models import (
    PARAMETERIZED_VALIDATOR_NAMES,
    VALIDATOR_LEVEL_FLOOR,
    VALIDATOR_NAMES,
    WorkflowSpec,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_TYPE = "task"


def _item() -> Item:
    prefix = BUILTIN_PREFIX[_TYPE]
    return Item(
        sequence_id=1,
        type=_TYPE,
        prefix=prefix,
        title="an item",
        slug="an-item",
        status="Draft",
        path=f"{BUILTIN_FOLDER[_TYPE]}/{prefix}-000001-an-item.md",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _entry(name: str, level: str) -> str:
    """A ``validators`` entry selecting *name* at *level*, with a placeholder parameter for a
    member that takes one (the spec is not loaded through Plane-1 here, so it need not be
    coherent)."""
    param = ":contract" if name == "ref_rule_target_present" else ""
    if name in PARAMETERIZED_VALIDATOR_NAMES and name != "ref_rule_target_present":
        param = ":80"
    return f"{name}{param}@{level}"


def _spec_selecting(name: str, level: str) -> WorkflowSpec:
    spec = bundled_spec()
    item_spec = spec.items[_TYPE].model_copy(update={"validators": [_entry(name, level)]})
    return spec.model_copy(update={"items": {**spec.items, _TYPE: item_spec}})


def _counting_catalog(calls: list[str]) -> dict[str, Validator]:
    def wrap(name: str) -> Validator:
        def counted(ctx: ValidatorContext) -> list[CheckIssue]:
            calls.append(name)
            return []

        return counted

    return {name: wrap(name) for name in CATALOG}


def _gate(spec: WorkflowSpec) -> list[str]:
    calls: list[str] = []
    db = SquadsDB(counter=1)
    ValidatorEngine(spec=spec, catalog=_counting_catalog(calls), squad_global={}).gate(_item(), db)
    return calls


def _report(spec: WorkflowSpec) -> list[str]:
    calls: list[str] = []
    db = SquadsDB(counter=1)
    item = _item()
    db.add(item)
    ValidatorEngine(spec=spec, catalog=_counting_catalog(calls), squad_global={}).report(
        db, {}, bodies={item.sequence_id: "body"}
    )
    return calls


@pytest.mark.parametrize("name", sorted(VALIDATOR_NAMES))
def test_the_gate_calls_a_member_at_error_and_not_at_warn(name: str) -> None:
    held_by_the_gate = not VALIDATOR_CONTEXT.get(name)
    at_error = _gate(_spec_selecting(name, "error"))
    assert (name in at_error) is held_by_the_gate
    if name in VALIDATOR_LEVEL_FLOOR:
        return  # a floor forbids selecting this member at warn
    assert name not in _gate(_spec_selecting(name, "warn"))


@pytest.mark.parametrize("name", sorted(VALIDATOR_NAMES))
@pytest.mark.parametrize("level", ["warn", "error"])
def test_report_calls_every_effective_member_at_either_level(name: str, level: str) -> None:
    if level == "warn" and name in VALIDATOR_LEVEL_FLOOR:
        pytest.skip("a floor forbids selecting this member at warn")
    assert name in _report(_spec_selecting(name, level))


def test_a_bundled_member_raised_to_error_is_called_by_the_gate_and_lowered_to_warn_is_not() -> (
    None
):
    assert "parent_in" in _gate(_spec_selecting("parent_in", "error"))
    assert "parent_in" not in _gate(_spec_selecting("parent_in", "warn"))
    assert "dangling_ref" in _gate(_spec_selecting("dangling_ref", "error"))
    assert "dangling_ref" not in _gate(bundled_spec())


def _raiser(ctx: ValidatorContext) -> list[CheckIssue]:
    raise RuntimeError("member raised")


def test_a_raising_member_at_warn_does_not_abort_a_write_and_at_error_does() -> None:
    db = SquadsDB(counter=1)
    catalog = {**CATALOG, "dangling_ref": _raiser}
    ValidatorEngine(spec=bundled_spec(), catalog=catalog, squad_global={}).gate(_item(), db)
    selected = _spec_selecting("dangling_ref", "error")
    with pytest.raises(RuntimeError, match="member raised"):
        ValidatorEngine(spec=selected, catalog=catalog, squad_global={}).gate(_item(), db)


def test_a_finding_at_error_still_refuses_with_its_own_message() -> None:
    def flags(ctx: ValidatorContext) -> list[CheckIssue]:
        return [CheckIssue("error", ctx.item.id, "stub refusal")]

    engine = ValidatorEngine(
        spec=_spec_selecting("dangling_ref", "error"),
        catalog={**CATALOG, "dangling_ref": flags},
        squad_global={},
    )
    with pytest.raises(SquadsError, match="stub refusal"):
        engine.gate(_item(), SquadsDB(counter=1))


@pytest.mark.parametrize("level", ["warn", "error"])
def test_a_member_needing_context_the_gate_lacks_is_skipped_at_either_level(level: str) -> None:
    for name in ("subentity_container_marker", "no_status_banner", "ref_rule_target_present"):
        assert name not in _gate(_spec_selecting(name, level))
