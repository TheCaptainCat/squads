"""A hyphenated ``prefix`` (legal per the workflow spec's own bare-key grammar, and accepted
by ``sq workflow lint``) must survive repad, the pre-merge block-shift renumber, and the
post-merge collision-fix renumber unscathed — every one of these hand-parses
``PREFIX-<digits>-<slug>`` filenames or ``PREFIX-<digits>`` ids, and splitting on the first
(rather than the last) hyphen corrupts the filename/id the moment the prefix itself contains
one.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads._services._service import Service
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import WorkflowSpec

pytestmark = pytest.mark.anyio

_HYPHENATED_PREFIX = "RUN-BOOK"


def _spec_with_hyphenated_task_prefix() -> WorkflowSpec:
    """The bundled spec, with ``task``'s own prefix shadowed to a hyphenated one — every other
    field (folder, lifecycle, parents, subentity_kind, ...) stays exactly as bundled."""
    base = load_workflow_spec()
    shadowed_task = base.items["task"].model_copy(update={"prefix": _HYPHENATED_PREFIX})
    return base.model_copy(
        update={
            "items": {**base.items, "task": shadowed_task},
            "prefix_to_type": {
                **{p: t for p, t in base.prefix_to_type.items() if t != "task"},
                _HYPHENATED_PREFIX: "task",
            },
        }
    )


def _svc(project) -> Service:
    return Service(project, spec=_spec_with_hyphenated_task_prefix())


async def test_repad_preserves_a_hyphenated_prefix(project):
    svc = _svc(project)
    task = (await create_item(svc, "task", "deploy runbook")).item
    assert task.id.startswith(f"{_HYPHENATED_PREFIX}-")
    original_bytes = svc.paths.abspath(task.path).read_bytes()
    original_path = svc.paths.abspath(task.path)

    await svc.repad(8)

    db = await svc.store.load()
    assert db.padding == 8
    reloaded = db.get(task.id)
    assert reloaded is not None
    task_folder = svc.paths.folder_for("task", spec=svc.spec)
    new_files = list(task_folder.glob(f"{_HYPHENATED_PREFIX}-*.md"))
    assert len(new_files) == 1
    # The file must actually have been renamed — under the bug the hand-rolled
    # ``partition("-")`` mistakes "BOOK" for the digit run, fails ``.isdigit()``, and the
    # file is silently skipped (left at the old width) rather than widened.
    assert not original_path.exists()
    stem = new_files[0].stem
    digit_run, _, slug = stem.removeprefix(f"{_HYPHENATED_PREFIX}-").partition("-")
    assert len(digit_run) == 8
    assert slug == "deploy-runbook"
    assert new_files[0].read_bytes() == original_bytes

    issues = await svc.check()
    assert issues == []


async def test_renumber_block_shift_preserves_a_hyphenated_prefix(project):
    svc = _svc(project)
    task = (await create_item(svc, "task", "shift me")).item

    result = await svc.renumber(from_seq=task.sequence_id, by=10)
    assert result.remap  # something was actually shifted

    db = await svc.store.load()
    moved = next(it for it in db.items.values() if it.title == "shift me")
    assert moved.id.startswith(f"{_HYPHENATED_PREFIX}-")
    new_path = svc.paths.abspath(moved.path)
    assert new_path.exists()
    assert new_path.name.startswith(f"{_HYPHENATED_PREFIX}-")
    # The corruption this guards against: a first-hyphen split turns "RUN-BOOK-000019" into
    # prefix "RUN" + digit-run "BOOK-000019" would fail `.isdigit()` and the whole rename
    # silently no-ops, or (post-repad) produces a doubled-number filename — either way `sq
    # check`/`sq list` stop seeing the item. Assert the corpus stays fully resolvable.
    assert (await svc.check()) == []


async def test_repair_renumber_collision_path_preserves_a_hyphenated_prefix(project):
    """The post-merge collision-fix path (``repair(renumber=True)``), exercised the way a
    merge actually produces a collision: two files claiming the same sequence number."""
    svc = _svc(project)
    task = (await create_item(svc, "task", "first")).item
    task_path = svc.paths.abspath(task.path)
    colliding_path = task_path.parent / task_path.name.replace("first", "second")
    text = task_path.read_text(encoding="utf-8").replace("first", "second")
    colliding_path.write_text(text, encoding="utf-8")

    result = await svc.repair(renumber=True)
    assert result.db.counter >= 2

    task_folder = svc.paths.folder_for("task", spec=svc.spec)
    files = sorted(p.name for p in task_folder.glob(f"{_HYPHENATED_PREFIX}-*.md"))
    assert len(files) == 2
    slugs = set()
    for name in files:
        stem = Path(name).stem
        remainder = stem.removeprefix(f"{_HYPHENATED_PREFIX}-")
        digit_run, _, slug = remainder.partition("-")
        # The corruption this guards against: a first-hyphen split mistakes "BOOK" for the
        # digit run and either no-ops the rename or, downstream, doubles the digit run into
        # the slug (e.g. "RUN-00000002-000001-first.md") — assert a single clean digit run
        # and the real slug survive instead.
        assert digit_run.isdigit()
        slugs.add(slug)
    assert slugs == {"first", "second"}

    issues = await svc.check()
    assert issues == []
