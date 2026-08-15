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

from _helpers import DEFAULT_TEST_AUTHOR
from squads._cli import app
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FEATURES = 200
_TASKS = 600
_BUGS = 200
# Total items = ROLE-1 (from minimal init) + _FEATURES + _TASKS + _BUGS
_TOTAL_ITEMS = 1 + _FEATURES + _TASKS + _BUGS


async def _build_scale_squad_async(
    tmp_path: Path,
    *,
    features: int = _FEATURES,
    tasks: int = _TASKS,
    bugs: int = _BUGS,
) -> service.Service:
    """Initialise a squad and populate it with items (async version).

    Uses ``no_claude=True`` to skip backend scaffolding (pointer files, CLAUDE.md
    section) so that the generation time is dominated by item I/O, not rendering.
    The minimal role spec registers one role (manager), which is sufficient as an
    author for all created items — every ``create`` call below passes it explicitly
    (``Service.create`` has no default author; see ``_services/_base.py``).

    ``features``/``tasks``/``bugs`` default to the ~1000-item scale corpus but can be
    shrunk to a handful for a cheap setup-path smoke test (see
    ``test_scale_fixture_builds_without_error`` below) without paying the full
    corpus-generation cost.
    """
    result = await service.init(root=tmp_path, roles_spec="minimal", no_claude=True)
    svc = service.Service(result.paths)

    feat_ids: list[str] = []
    for i in range(features):
        r = await svc.create(
            "feature",
            f"Feature {i}",
            description=f"Generated feature {i} for scale testing.",
            author=DEFAULT_TEST_AUTHOR,
        )
        feat_ids.append(r.item.id)

    # tasks distributed across all features (3 per feature on average, at full scale)
    for i in range(tasks):
        await svc.create(
            "task",
            f"Task {i}",
            parent=feat_ids[i % len(feat_ids)],
            author=DEFAULT_TEST_AUTHOR,
        )

    for i in range(bugs):
        await svc.create(
            "bug",
            f"Bug {i}",
            description=f"Generated bug {i} for scale testing.",
            author=DEFAULT_TEST_AUTHOR,
        )

    return svc


def _build_scale_squad(tmp_path: Path) -> service.Service:
    """Sync wrapper around _build_scale_squad_async for use in sync test functions."""
    import anyio

    return anyio.run(_build_scale_squad_async, tmp_path)


# ---------------------------------------------------------------------------
# Setup-path canary (NOT marked slow — runs in the default fast suite)
# ---------------------------------------------------------------------------
#
# The five tests below are gated behind --run-slow, so a setup-only defect in
# _build_scale_squad_async (e.g. a required constructor argument the fixture stopped
# passing) is invisible to a bare `uv run pytest` — the whole module can be broken for
# every wall-clock bound it claims to hold, and CI's default `uv run pytest` (no
# --run-slow in .github/workflows/test.yml) does not catch it either. This canary
# exercises the exact same setup path — service.init + svc.create through the fixture —
# at a corpus of 1 item per type instead of ~1000, so it costs milliseconds and always
# runs. It asserts nothing about timing; it only proves the corpus-building call path
# still succeeds. A regression here means the slow tests below cannot even reach their
# own assertions, which is a different failure mode than a bound being exceeded and
# must not be confused with one.


async def test_scale_fixture_builds_without_error(tmp_path: Path) -> None:
    """The scale fixture's setup path must succeed at a trivial size, cheaply and by default.

    Guards against a change to item-creation requirements (e.g. author becoming mandatory)
    that isn't reflected in this fixture, which breaks all five @pytest.mark.slow tests in
    their own setup — invisibly, until someone remembers --run-slow. This test has no such
    opt-in.
    """
    svc = await _build_scale_squad_async(tmp_path, features=1, tasks=1, bugs=1)

    items = await svc.list_items()
    assert len(items) == 1 + 1 + 1 + 1, f"expected 4 items (role + 1/1/1), got {len(items)}"


# ---------------------------------------------------------------------------
# Scale tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_scale_list_completes_within_bound(tmp_path: Path) -> None:
    """list_items() over ~1000 items must complete in under 5 seconds."""
    svc = await _build_scale_squad_async(tmp_path)

    t0 = time.perf_counter()
    items = await svc.list_items()
    elapsed = time.perf_counter() - t0

    assert len(items) == _TOTAL_ITEMS, f"expected {_TOTAL_ITEMS} items, got {len(items)}"
    assert elapsed < 5.0, f"list_items took {elapsed:.2f}s — expected < 5s"


@pytest.mark.slow
async def test_scale_search_completes_within_bound(tmp_path: Path) -> None:
    """search() scanning ~1000 items must complete in under 5 seconds."""
    svc = await _build_scale_squad_async(tmp_path)

    t0 = time.perf_counter()
    results, _skipped = await svc.search("feature")
    elapsed = time.perf_counter() - t0

    # Every feature's title / description contains "feature" — at least one hit expected.
    assert len(results) > 0, "search returned no results"
    assert elapsed < 5.0, f"search took {elapsed:.2f}s — expected < 5s"


@pytest.mark.slow
async def test_scale_repair_completes_within_bound(tmp_path: Path) -> None:
    """repair() (full index rebuild from disk) over ~1000 items must complete in under 10s."""
    svc = await _build_scale_squad_async(tmp_path)

    # Nuke the index to force a full disk scan.
    svc.paths.index_path.unlink()

    t0 = time.perf_counter()
    result = await svc.repair()
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
