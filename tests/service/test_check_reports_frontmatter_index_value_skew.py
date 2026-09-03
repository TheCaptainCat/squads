"""``sq check`` reports a frontmatter/index value divergence on *any* top-level field, not
only the two hand-picked ``status``/``parent`` drift predicates it folded in. The three
non-negotiables the accepted decision settles, each with its own test below:

1. ``frontmatter_skew`` is reused *verbatim* — check reports precisely when the write seam's
   own :func:`~squads._itemfile.ensure_no_skew` would raise (the equivalence property).
2. ``warn`` level, exit code unchanged.
3. No new I/O — the rule is built entirely on data ``_scan_for_check`` already holds.
"""

from pathlib import Path

import anyio
import pytest

from _helpers import create_item
from squads import _itemfile as itemfile
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter
from squads._services import _maintenance as maintenance

pytestmark = pytest.mark.anyio


def _edit_frontmatter(path: Path, **fields: object) -> None:
    """Directly rewrite frontmatter fields on a squad-data file, bypassing the service — the
    only way to construct a frontmatter/index mismatch these tests need."""
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm.update(fields)
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _crash_the_index_commit(svc, monkeypatch, mutate) -> None:
    """Run *mutate* with the index commit faulted so the markdown write inside the
    transaction stands but the index never sees it — the durability model's own
    markdown-ahead-of-index skew shape."""
    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    try:
        with pytest.raises(OSError):
            await mutate()
    finally:
        monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)


# --- the interrupted-write shape


async def test_interrupted_write_on_title_is_reported_both_directions(svc, monkeypatch):
    task = (await create_item(svc, "task", "original title")).item
    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, title="interrupted rename", force=True)
    )

    issues = await svc.check()
    hit = next(i for i in issues if i.item == task.id and "title" in i.message)
    assert hit.level == "warn"
    assert "drift between frontmatter and index" in hit.message
    # Falsification: the narrower status/parent-only predicate this generalises would have
    # said nothing about this exact corpus — status and parent never changed, only title did.
    assert not any(
        i.item == task.id and ("status drift" in i.message or "parent drift" in i.message)
        for i in issues
    )


async def test_interrupted_write_on_priority_is_reported(svc, monkeypatch):
    """A field with no bespoke predicate today — proves the generalisation is real, not just
    a rename of the status/parent pair."""
    task = (await create_item(svc, "task", "t")).item
    original_priority = task.priority
    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, priority="high", force=True)
    )

    reloaded = await svc.get(task.id)
    assert reloaded.priority == original_priority  # index never saw the change

    issues = await svc.check()
    hit = next(i for i in issues if i.item == task.id and "priority" in i.message)
    assert hit.level == "warn"


# --- pre-fix corpus stays clean


async def test_a_never_synced_role_override_reports_nothing_before_and_after_sync(svc):
    """An override declaring ``full_name``/``mission`` that no sync has yet applied: both
    stored homes still carry the same (old) value, so there is no divergence to report — the
    test that would catch a rule built on "stored title vs resolved name" instead of on the
    two stored homes."""
    from squads import __version__

    item = await svc.activate_role("qa")
    override_dir = svc.paths.squad_dir / ".overrides" / "roles"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "qa.toml").write_text(
        f'# squads:override-base:{__version__}\nfull_name = "Quinn Assurance"\n'
        'mission = "Own quality end to end."\n',
        encoding="utf-8",
    )

    issues = await svc.check()
    assert not any(i.item == item.id for i in issues), issues

    await svc.sync()
    issues = await svc.check()
    assert not any(i.item == item.id for i in issues), issues


async def test_a_permanently_exempt_extra_key_is_still_never_reported(svc):
    """A role's catalog-shaped ``extra`` field (``RoleDef.extra_keys()``) can sit ahead of the
    index by design (``PERMITTED_EXTRA_SKEW``) on a squad a pre-mirror release last synced —
    functional proof the exemption still holds under the generalised rule, not a pinned
    literal copy of the set (which the widening must not touch, and does not: this behaviour
    comes from ``frontmatter_skew`` unmodified). Constructed directly on disk rather than via
    a resync writer: the resolved-skills cache this test used to reproduce the shape through
    (``link_role``) is gone along with the cache itself."""
    role = await svc.activate_role("qa")
    path = svc.paths.abspath(role.path)
    fm = read_frontmatter(path=path)
    extra = dict(fm["extra"])
    extra["model"] = "haiku"  # a `PERMITTED_EXTRA_SKEW` member, on a non-dev role
    _edit_frontmatter(path, extra=extra)

    issues = await svc.check()
    assert not any(i.item == role.id for i in issues), issues


# --------------------------------------------------------------------------- equivalence property


async def test_check_reports_precisely_when_ensure_no_skew_would_raise(svc):
    """The decision's equivalence property, stated as one property rather than two lists: for a
    given ``(text, item)`` pair, check reports a divergence exactly when
    :func:`~squads._itemfile.ensure_no_skew` raises — not merely a similarly-worded message."""
    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath(task.path)
    original_text = path.read_text(encoding="utf-8")
    original_fm = read_frontmatter(text=original_text)

    def _with(**fields: object) -> str:
        fm = dict(original_fm)
        fm.update(fields)
        return sections.replace_frontmatter(original_text, fm)

    cases = [
        original_text,  # healthy
        _with(status="InProgress"),
        _with(priority="high"),
        _with(title="a different title"),
        _with(status="InProgress", priority="high"),
    ]
    default_kind = svc.spec.default_ref_kind()
    for case_text in cases:
        try:
            itemfile.ensure_no_skew(case_text, task, default_kind=default_kind)
            raised = False
        except SquadsError:
            raised = True
        fdata = read_frontmatter(text=case_text)
        issue = maintenance._value_skew_issue(task, case_text, fdata, default_kind=default_kind)
        assert (issue is not None) == raised, (case_text, issue, raised)


# --------------------------------------------------------------------------- confirm round


async def test_a_skew_resolved_by_a_racing_repair_is_not_reported(svc, monkeypatch):
    task = (await create_item(svc, "task", "t")).item
    _edit_frontmatter(svc.paths.abspath(task.path), title="disk-only title")

    started = anyio.Event()
    release = anyio.Event()
    orig_scan = svc._scan_for_check

    async def paused_scan():
        started.set()
        await release.wait()
        return await orig_scan()

    svc._scan_for_check = paused_scan

    issues: list[maintenance.CheckIssue] = []

    async def run_check() -> None:
        issues.extend(await svc.check())

    async def run_repair() -> None:
        await started.wait()
        await svc.repair()
        release.set()

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_check)
        tg.start_soon(run_repair)

    assert not any(i.item == task.id and "title" in i.message for i in issues), issues


# --- exit code / folded predicates


async def test_exit_code_unchanged_on_a_value_divergence_only_squad(svc, monkeypatch, invoke):
    task = (await create_item(svc, "task", "t")).item
    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, title="interrupted", force=True)
    )

    r = await invoke(["check"])
    assert r.exit_code == 0, r.output
    assert "title" in r.output


async def test_status_and_parent_drift_still_report_with_direction_intact(svc):
    """The folded-in predicates' own coverage (and direction naming) must survive the
    generalisation."""
    task = (await create_item(svc, "task", "t")).item
    _edit_frontmatter(svc.paths.abspath(task.path), status="InProgress")
    issues = await svc.check()
    hit = next(i for i in issues if i.item == task.id and "status" in i.message)
    assert hit.level == "warn"

    other = (await create_item(svc, "epic", "parent one")).item
    another = (await create_item(svc, "epic", "parent two")).item
    task2 = (await create_item(svc, "feature", "f", parent=other.id)).item
    _edit_frontmatter(svc.paths.abspath(task2.path), parent=another.id)
    issues = await svc.check()
    hit = next(i for i in issues if i.item == task2.id and "parent" in i.message)
    assert hit.level == "warn"


# --------------------------------------------------------------------------- no new I/O


async def test_no_new_index_load_or_file_read_on_a_clean_board(svc, monkeypatch):
    from squads import _aio

    await create_item(svc, "task", "a")
    await create_item(svc, "task", "b")

    load_calls = 0
    orig_load = svc.store.load

    async def counted_load(**kwargs):
        nonlocal load_calls
        load_calls += 1
        return await orig_load(**kwargs)

    monkeypatch.setattr(svc.store, "load", counted_load)

    read_paths: list[Path] = []
    orig_read = _aio.read_text

    async def counted_read(path: Path) -> str:
        read_paths.append(path)
        return await orig_read(path)

    monkeypatch.setattr(_aio, "read_text", counted_read)

    issues = await svc.check()
    assert not any(i.level == "error" for i in issues), issues
    assert load_calls == 1
    assert len(read_paths) == len(set(read_paths)), "a clean board must never re-read a file"
