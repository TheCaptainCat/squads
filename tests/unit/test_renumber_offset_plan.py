"""``MaintenanceMixin._offset_plan`` (``sq renumber``'s pure boundary math): requires exactly
one of ``onto``/``by``, ``--onto`` auto-computes the minimal safe offset above both ranges, and
a safe ``--by`` shifts correctly but still warns it cannot certify disjointness the way
``--onto`` can. Pure function — fed synthetic (id, path, type, title, seq) records, no
filesystem or squad involved.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._services._maintenance import MaintenanceMixin


def _fake_records(*seqs: int, prefix: str = "TASK") -> list[tuple[str, Path, str, str, int]]:
    return [(f"{prefix}-{seq}", Path(f"/fake/{prefix}-{seq}.md"), "task", "x", seq) for seq in seqs]


def _seqs_from(remap: dict[str, str]) -> dict[int, int]:
    return {int(k.rsplit("-", 1)[-1]): int(v.rsplit("-", 1)[-1]) for k, v in remap.items()}


def test_offset_plan_requires_exactly_one_of_onto_or_by() -> None:
    records = _fake_records(3)
    with pytest.raises(SquadsError, match="exactly one"):
        MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=5, onto=None, by=None, padding=6
        )
    with pytest.raises(SquadsError, match="exactly one"):
        MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=5, onto=10, by=3, padding=6
        )


def test_offset_plan_onto_computes_the_minimal_safe_offset_above_both_ranges() -> None:
    records = _fake_records(3, 4, 5)
    for onto, counter in [(10, 5), (2, 5), (5, 5)]:
        remap, _renames, warning = MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=counter, onto=onto, by=None, padding=6
        )
        assert warning is None  # --onto never warns — it fully certifies disjointness
        delta = max(onto, counter) + 1 - 3
        assert _seqs_from(remap) == {3: 3 + delta, 4: 4 + delta, 5: 5 + delta}


def test_offset_plan_by_shifts_correctly_but_warns_it_cannot_certify_the_other_branch_clears() -> (
    None
):
    records = _fake_records(3, 4, 5)
    remap, renames, warning = MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
        records, from_seq=3, counter=5, onto=None, by=3, padding=6
    )
    assert warning is not None and "onto" in warning.lower()
    assert _seqs_from(remap) == {3: 6, 4: 7, 5: 8}
    assert len(renames) == 3
