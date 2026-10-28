"""The squad the read-command tests share: items that differ in type, status, parent, priority,
label and assignee, a dependency, a closed item and a comment that mentions a role."""

import asyncio
from pathlib import Path

from typer.testing import CliRunner

from squads._cli import app
from tests._helpers import create_item, make_service
from tests._squads import init_minimal, paths_of

FEATURE = 2
PARSER = 3
RANKING = 4
INDEX_DECISION = 5
CRASH = 6
REVIEW = 7


async def _populate(root: Path) -> None:
    svc = make_service(paths_of(root))
    feature = await create_item(
        svc, "feature", "Search", priority="high", labels=["core"], assignee="manager"
    )
    await svc.add_block(feature.item.id, "story", "Query the index")
    await svc.add_block(feature.item.id, "story", "Rank the results")
    parser = await create_item(
        svc,
        "task",
        "Parse queries",
        parent=feature.item.id,
        priority="urgent",
        labels=["parser"],
        assignee="manager",
    )
    await svc.set_status(parser.item.id, "InProgress", force=True)
    await svc.add_block(parser.item.id, "subtask", "Tokenise the input", story="US1")
    await svc.add_block(parser.item.id, "subtask", "Parse the operators")
    await svc.update_block(parser.item.id, "subtask", "ST2", status="Done", force=True)
    ranking = await create_item(svc, "task", "Rank results", parent=feature.item.id, priority="low")
    await svc.add_ref(ranking.item.id, parser.item.id, kind="depends-on")
    await create_item(svc, "decision", "Pick an index", description="Why an inverted index")
    crash = await create_item(svc, "bug", "Empty query crash", priority="medium")
    await svc.update(crash.item.id, assignee="manager")
    await svc.set_status(crash.item.id, "Verified", force=True)
    review = await create_item(svc, "review", "Review the parser", labels=["parser"])
    await svc.add_block(
        review.item.id, "finding", "Unbounded recursion", fields={"severity": "High"}
    )
    await svc.add_ref(ranking.item.id, review.item.id, kind="related")
    await svc.add_ref(review.item.id, crash.item.id, kind="related")
    await svc.update_block(review.item.id, "finding", "F1", assignee="manager")
    await svc.comment(parser.item.id, ["@manager please look at the tokeniser"], as_slug="manager")


def init_readable(root: Path) -> None:
    """The `minimal` squad plus the items above."""
    init_minimal(root)
    asyncio.run(_populate(root))


async def _add_operator(root: Path) -> None:
    svc = make_service(paths_of(root))
    await svc.add_operator("Pierre Chat")
    await svc.comment(f"REV-{REVIEW}", ["@op-pierre what is your view?"], as_slug="manager")


def init_readable_with_operator(root: Path) -> None:
    """The squad above plus the operator `op-pierre`, who is mentioned once and assigned nothing."""
    init_readable(root)
    asyncio.run(_add_operator(root))


def init_readable_with_history(root: Path) -> None:
    """The squad above plus a comment written by `manager` on the next day, through the CLI so
    the reflog records its actor."""
    init_readable(root)
    argv = [
        "--at",
        "2026-06-08T09:00:00Z",
        "task",
        "4",
        "comment",
        "--as",
        "manager",
        "-m",
        "again",
    ]
    result = CliRunner().invoke(app, argv)
    assert result.exit_code == 0, result.output


def lines(output: str) -> list[str]:
    """The lines of *output* without the padding a table adds at the end of a line."""
    return [line.rstrip() for line in output.splitlines()]
