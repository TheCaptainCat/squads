"""``_check_coverage`` used to reparse the bundled ``playbook.toml`` a second time on every
single ``load_playbook()`` call, purely to recover the bundled ``[types]`` key set (a constant
of the release) — on top of the reparse ``_base_raw_for`` already does (load-bearing there, per
the isolation guarantee: see that function's docstring). The key set itself carries no aliasing
risk (a ``frozenset`` of plain strings) and is cached process-wide now.
"""

from squads._interactions import _loader
from squads._roles._catalog import get_catalog


def test_the_bundled_type_key_set_is_read_from_disk_at_most_once_across_repeated_loads(
    monkeypatch,
) -> None:
    read_calls: list[int] = []
    original = _loader._read_bundled_bytes

    def _counting_read() -> bytes:
        read_calls.append(1)
        return original()

    monkeypatch.setattr(_loader, "_read_bundled_bytes", _counting_read)
    _loader._bundled_type_names.cache_clear()

    catalog = get_catalog()
    for _ in range(3):
        _loader.load_playbook(catalog)

    # One read per call from _base_raw_for (deliberately un-cached — see its own isolation
    # argument), plus exactly ONE extra read total for the coverage key set (cached after the
    # first call) — not one extra read PER call, which is what the prior code paid.
    assert len(read_calls) == 3 + 1
