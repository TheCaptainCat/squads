"""Scale sanity test: generate a ~1000-item squad and verify that list, search,
repair, and the sq list / sq tree CLI commands all complete within generous
wall-clock bounds.

Run with ``uv run pytest -m slow`` (excluded from the fast suite by default).

Time bounds are intentionally loose (10-25x above the locally-observed baseline)
so the test is stable across CI platforms (linux/macos/windows) while still
catching pathological O(n^2) or full-rescan regressions.
"""

import time
from pathlib import Path

import pytest

from squads._cli import app
from squads._models._enums import ItemType
from squads._services import _service as service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FEATURES = 200
_TASKS = 600
_BUGS = 200
# Total items = ROLE-1 (from minimal init) + _FEATURES + _TASKS + _BUGS
_TOTAL_ITEMS = 1 + _FEATURES + _TASKS + _BUGS


def _build_scale_squad(tmp_path: Path) -> service.Service:
    """Initialise a squad and populate it with ~1000 items.

    Uses ``no_claude=True`` to skip backend scaffolding (pointer files, CLAUDE.md
    section) so that the generation time is dominated by item I/O, not rendering.
    The minimal role spec registers one role (manager), which is sufficient as an
    author for all created items.
    """
    result = service.init(root=tmp_path, roles_spec="minimal", no_claude=True)
    svc = service.Service(result.paths)

    # 200 features
    feat_ids: list[str] = []
    for i in range(_FEATURES):
        r = svc.create(
            ItemType.FEATURE,
            f"Feature {i}",
            description=f"Generated feature {i} for scale testing.",
        )
        feat_ids.append(r.item.id)

    # 600 tasks — distributed across all features (3 per feature on average)
    for i in range(_TASKS):
        svc.create(
            ItemType.TASK,
            f"Task {i}",
            parent=feat_ids[i % len(feat_ids)],
        )

    # 200 bugs
    for i in range(_BUGS):
        svc.create(
            ItemType.BUG,
            f"Bug {i}",
            description=f"Generated bug {i} for scale testing.",
        )

    return svc


# ---------------------------------------------------------------------------
# Scale tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_scale_list_completes_within_bound(tmp_path: Path) -> None:
    """list_items() over ~1000 items must complete in under 5 seconds."""
    svc = _build_scale_squad(tmp_path)

    t0 = time.perf_counter()
    items = svc.list_items()
    elapsed = time.perf_counter() - t0

    assert len(items) == _TOTAL_ITEMS, f"expected {_TOTAL_ITEMS} items, got {len(items)}"
    assert elapsed < 5.0, f"list_items took {elapsed:.2f}s — expected < 5s"


@pytest.mark.slow
def test_scale_search_completes_within_bound(tmp_path: Path) -> None:
    """search() scanning ~1000 items must complete in under 5 seconds."""
    svc = _build_scale_squad(tmp_path)

    t0 = time.perf_counter()
    results = svc.search("feature")
    elapsed = time.perf_counter() - t0

    # Every feature's title / description contains "feature" — at least one hit expected.
    assert len(results) > 0, "search returned no results"
    assert elapsed < 5.0, f"search took {elapsed:.2f}s — expected < 5s"


@pytest.mark.slow
def test_scale_repair_completes_within_bound(tmp_path: Path) -> None:
    """repair() (full index rebuild from disk) over ~1000 items must complete in under 10s."""
    svc = _build_scale_squad(tmp_path)

    # Nuke the index to force a full disk scan.
    svc.paths.index_path.unlink()

    t0 = time.perf_counter()
    result = svc.repair()
    elapsed = time.perf_counter() - t0

    assert len(result.db.items) == _TOTAL_ITEMS, (
        f"repair rebuilt {len(result.db.items)} items, expected {_TOTAL_ITEMS}"
    )
    assert result.missing_ids == [], f"repair reported missing IDs: {result.missing_ids}"
    assert elapsed < 10.0, f"repair took {elapsed:.2f}s — expected < 10s"


@pytest.mark.slow
def test_scale_cli_list_completes_within_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runner: pytest.FixtureRequest
) -> None:
    """``sq list --all`` over ~1000 items must complete in under 10 seconds."""
    monkeypatch.chdir(tmp_path)
    _build_scale_squad(tmp_path)

    from typer.testing import CliRunner as _Runner

    cli_runner = _Runner()

    t0 = time.perf_counter()
    result = cli_runner.invoke(app, ["list", "--all"])
    elapsed = time.perf_counter() - t0

    assert result.exit_code == 0, f"sq list --all failed: {result.output}"
    assert elapsed < 10.0, f"sq list --all took {elapsed:.2f}s — expected < 10s"


@pytest.mark.slow
def test_scale_cli_tree_completes_within_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``sq tree --all`` and ``sq tree --all --json`` over ~1000 items must each complete in
    under 10 seconds.
    """
    monkeypatch.chdir(tmp_path)
    _build_scale_squad(tmp_path)

    from typer.testing import CliRunner as _Runner

    cli_runner = _Runner()

    t0 = time.perf_counter()
    result_tree = cli_runner.invoke(app, ["tree", "--all"])
    elapsed_tree = time.perf_counter() - t0

    assert result_tree.exit_code == 0, f"sq tree --all failed: {result_tree.output}"
    assert elapsed_tree < 10.0, f"sq tree --all took {elapsed_tree:.2f}s — expected < 10s"

    t1 = time.perf_counter()
    result_json = cli_runner.invoke(app, ["tree", "--all", "--json"])
    elapsed_json = time.perf_counter() - t1

    assert result_json.exit_code == 0, f"sq tree --all --json failed: {result_json.output}"
    assert elapsed_json < 10.0, f"sq tree --all --json took {elapsed_json:.2f}s — expected < 10s"
