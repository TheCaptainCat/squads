"""The bulk importer's pre-flight skew guard (`_services/_import.py::_check_target_skew`)
catches a missing target file and returns quietly rather than raising -- deferring the claim to
`sq check`'s own reconciliation rather than failing the whole import over a state `check` is
already positioned to report.

This is one of the two call sites `_aio.read_text`'s decode/not-found guards must never touch
(see `tests/unit/test_read_text_decode_and_not_found_guards.py`'s module docstring for the
other, `check`'s confirm round): a blanket not-found conversion in the shared read helper would
turn this deliberate "defer, don't fail" behaviour into a failed import instead. If this test
starts failing, the not-found guard has been placed in the shared helper by mistake.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


def _lines(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(e) for e in events)


async def test_a_target_whose_file_is_missing_still_plans_rather_than_failing(svc):
    task = (await svc.create("task", "Target whose file goes missing")).item
    svc.paths.abspath(task.path).unlink()

    text = _lines({"op": "status", "target": task.id, "status": "InProgress"})
    result = await svc.import_events(text, dry_run=True)

    # The skew guard defers the claim -- it never raises, and never reports an issue of its
    # own for this target (a missing file is `sq check`'s claim to make, not this guard's).
    assert not any(task.id in issue.message for issue in result.plan.issues)


async def test_a_missing_target_coexists_with_an_unrelated_validation_issue(svc):
    """The missing-file skip never masks or stops collection of a real problem elsewhere in
    the same batch -- it only ever declines to add its own issue."""
    task = (await svc.create("task", "Target whose file goes missing")).item
    svc.paths.abspath(task.path).unlink()

    text = _lines(
        {"op": "status", "target": task.id, "status": "InProgress"},
        {"op": "status", "target": "no-such-handle-or-id", "status": "InProgress"},
    )
    result = await svc.import_events(text, dry_run=True)

    assert not result.plan.ok
    assert any("no-such-handle-or-id" in i.message for i in result.plan.issues)
    assert not any(task.id in i.message for i in result.plan.issues)
