"""Every opt-in policy check against every type row of the selection table: its plain entry
either loads, or is refused at spec load with a message naming the type, the entry and what is
missing. The registry decides every cell, and `sq workflow lint` reports exactly what the loader
refuses.
"""

import pytest

from _selection_table import (
    MEMBERS,
    Member,
    TypeRow,
    override_toml,
    write_override,
)
from squads._errors import SquadsError
from squads._services import _service as service
from squads._workflow._loader import lint_workflow_spec

pytestmark = pytest.mark.anyio

_CELLS = [(m, r) for m in MEMBERS.values() for r in m.all_rows()]
_IDS = [f"{m.name}-{r.id}" for m, r in _CELLS]


def test_every_member_decides_every_row() -> None:
    for member in MEMBERS.values():
        assert set(member.cells) == {r.id for r in member.all_rows()}, member.name


@pytest.mark.parametrize(("member", "row"), _CELLS, ids=_IDS)
async def test_the_plain_entry_loads_or_is_refused_as_the_registry_decides(
    project, member: Member, row: TypeRow
) -> None:
    write_override(project.squad_dir, override_toml(row, member.plain))
    errors = [f for f in lint_workflow_spec(project.squad_dir) if f[0] == "error"]
    refusal = member.cells[row.id]
    if refusal is None:
        assert errors == []
        service.open_service()
        return
    text = " ".join(f"{f[1]} {f[2]}" for f in errors)
    assert row.type in text
    assert member.plain[0] in text
    assert refusal in text
    with pytest.raises(SquadsError) as raised:
        service.open_service()
    assert member.plain[0] in str(raised.value)
    assert refusal in str(raised.value)
