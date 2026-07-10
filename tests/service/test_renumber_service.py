"""``Service.renumber()`` itself (the CLI wiring is proven separately at
tests/integration/test_renumber_cli.py): requires exactly one of ``onto``/``by``, records
whichever boundary the operator supplied in the reflog summary line, and is a clean no-op —
including on the index-exists-but-nothing-to-shift path — when nothing matches ``from_seq``.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_renumber_requires_exactly_one_of_onto_or_by(svc):
    with pytest.raises(SquadsError, match="exactly one"):
        await svc.renumber(from_seq=1)
    with pytest.raises(SquadsError, match="exactly one"):
        await svc.renumber(from_seq=1, onto=5, by=3)


async def test_renumber_with_a_by_offset_records_by_and_leaves_onto_null_in_the_reflog(svc):
    from squads._index._reflog import read_lines, reflog_path

    task = (await svc.create("task", "shift-me")).item

    result = await svc.renumber(from_seq=task.sequence_id, by=5)

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    entry = next(ln for ln in lines if ln.op == "renumber")
    assert entry.delta["onto"] is None
    assert entry.delta["by"] == 5
    assert entry.delta["remap"] == result.remap


async def test_renumber_with_nothing_to_shift_is_a_noop_even_though_the_index_already_exists(svc):
    await svc.create("task", "unrelated")  # ensures the index file exists on disk
    result = await svc.renumber(from_seq=999, onto=5)
    assert result.remap == {}
