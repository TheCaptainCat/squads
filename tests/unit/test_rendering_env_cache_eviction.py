"""The per-squad-dir Jinja Environment cache is a bounded CODE cache (compiled templates),
not an unbounded one: a long-lived process touching more distinct squad dirs than the cache's
capacity must evict the least-recently-used entry rather than retain an Environment (and its
override loader) for every squad it has ever seen. Bundled-only (`None`) and
`invalidate_squad_dir` continue to work at any cache size.
"""

from pathlib import Path

from squads._rendering import _engine
from squads._rendering._engine import invalidate_squad_dir, set_active_squad_dir


def _touch(squad_dir: Path | None) -> None:
    """Force an Environment to be built/cached for *squad_dir* without rendering a template."""
    set_active_squad_dir(squad_dir)
    _engine._env()  # pyright: ignore[reportPrivateUsage]


def test_the_env_cache_never_grows_past_its_capacity(tmp_path: Path) -> None:
    cap = _engine._ENV_CACHE_MAX_SIZE  # pyright: ignore[reportPrivateUsage]
    dirs = [tmp_path / f"squad-{i}" for i in range(cap + 5)]
    for d in dirs:
        d.mkdir()
        set_active_squad_dir(d)
        _engine._env()  # pyright: ignore[reportPrivateUsage]
        assert len(_engine._env_cache) <= cap  # pyright: ignore[reportPrivateUsage]


def test_touching_more_dirs_than_capacity_evicts_the_least_recently_used_first(
    tmp_path: Path,
) -> None:
    cap = _engine._ENV_CACHE_MAX_SIZE  # pyright: ignore[reportPrivateUsage]
    dirs = [tmp_path / f"squad-{i}" for i in range(cap)]
    for d in dirs:
        d.mkdir()
        set_active_squad_dir(d)
        _engine._env()  # pyright: ignore[reportPrivateUsage]
    assert dirs[0] in _engine._env_cache  # pyright: ignore[reportPrivateUsage]

    # One more distinct dir past capacity must evict the oldest (dirs[0]), not any other.
    extra = tmp_path / "squad-extra"
    extra.mkdir()
    set_active_squad_dir(extra)
    _engine._env()  # pyright: ignore[reportPrivateUsage]

    cache = _engine._env_cache  # pyright: ignore[reportPrivateUsage]
    assert len(cache) == cap
    assert dirs[0] not in cache
    assert extra in cache
    assert all(d in cache for d in dirs[1:])


def test_re_touching_an_entry_marks_it_most_recently_used_so_it_survives_eviction(
    tmp_path: Path,
) -> None:
    cap = _engine._ENV_CACHE_MAX_SIZE  # pyright: ignore[reportPrivateUsage]
    dirs = [tmp_path / f"squad-{i}" for i in range(cap)]
    for d in dirs:
        d.mkdir()
        set_active_squad_dir(d)
        _engine._env()  # pyright: ignore[reportPrivateUsage]

    # Re-touch the oldest entry so it becomes most-recently-used.
    set_active_squad_dir(dirs[0])
    _engine._env()  # pyright: ignore[reportPrivateUsage]

    extra = tmp_path / "squad-extra"
    extra.mkdir()
    set_active_squad_dir(extra)
    _engine._env()  # pyright: ignore[reportPrivateUsage]

    cache = _engine._env_cache  # pyright: ignore[reportPrivateUsage]
    # dirs[1] was the actual least-recently-used one now, not dirs[0].
    assert dirs[0] in cache
    assert dirs[1] not in cache


def test_invalidate_squad_dir_still_evicts_a_single_entry_at_any_cache_size(
    tmp_path: Path,
) -> None:
    squad_dir = tmp_path / "squad"
    squad_dir.mkdir()
    _touch(squad_dir)
    assert squad_dir in _engine._env_cache  # pyright: ignore[reportPrivateUsage]

    invalidate_squad_dir(squad_dir)
    assert squad_dir not in _engine._env_cache  # pyright: ignore[reportPrivateUsage]


def test_bundled_only_none_path_is_unaffected_by_bounding() -> None:
    _touch(None)
    assert None in _engine._env_cache  # pyright: ignore[reportPrivateUsage]
