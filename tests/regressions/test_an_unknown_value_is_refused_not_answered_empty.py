"""Listing and log options refuse a value they cannot apply instead of answering with an empty
or unsorted result."""

import pytest

from tests._readable import lines

pytestmark = pytest.mark.anyio

OPS = (
    "create, status, update, body, view, comment, comment_edit, comment_remove, subentity, ref, "
    "link, retype, default_role, remove, repair, renumber, migrate, rename-type, "
    "rename-status, rename-field, rename-kind"
)


async def _run(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(list(args))
    return result.exit_code, lines(result.output)


async def test_a_sort_field_that_is_not_declared_is_refused(readable, invoke) -> None:
    expected = (1, ["error: unknown sort field 'ghost' (one of: priority, severity)"])
    assert await _run(invoke, "list", "--sort", "ghost") == expected
    assert await _run(invoke, "tree", "--sort", "ghost") == expected


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (
            ("list", "--badge", "priority=ghost"),
            "unknown priority 'ghost' (one of: urgent, high, medium, low)",
        ),
        (
            ("tree", "--min-badge", "ghost=x"),
            "unknown badge field 'ghost' (one of: priority, severity)",
        ),
    ],
)
async def test_a_badge_filter_with_an_unknown_field_or_value_is_refused(
    readable, invoke, args, message
) -> None:
    assert await _run(invoke, *args) == (1, [f"error: {message}"])


async def test_a_reflog_operation_that_does_not_exist_is_refused(readable, invoke) -> None:
    assert await _run(invoke, "reflog", "--op", "ghost") == (
        1,
        [f"error: unknown operation 'ghost' (one of: {OPS})"],
    )


async def test_a_negative_depth_is_refused(readable, invoke) -> None:
    assert await _run(invoke, "tree", "--depth", "-1") == (
        2,
        [
            "Usage: sq tree [OPTIONS] [ROOT_ID]",
            "Try 'sq tree --help' for help.",
            "╭─ Error ──────────────────────────────────────────────────────────────────────╮",
            "│ Invalid value for '--depth': must be 0 or more                               │",
            "╰──────────────────────────────────────────────────────────────────────────────╯",
        ],
    )
