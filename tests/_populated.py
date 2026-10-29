"""The populated squad the surface tests share: one item of each kind of sub-entity host.

The counter starts after the squad's single role, so the numbers below are fixed.
"""

import asyncio
from pathlib import Path

from tests._helpers import create_item, make_service
from tests._squads import init_minimal, paths_of

FEATURE = 2
TASK = 3
REVIEW = 4


async def _populate(root: Path) -> None:
    svc = make_service(paths_of(root))
    feature = await create_item(svc, "feature", "Search")
    await svc.add_block(feature.item.id, "story", "Query the index")
    await svc.add_block(feature.item.id, "story", "Rank the results")
    task = await create_item(svc, "task", "Build the query parser", parent=feature.item.id)
    await svc.add_block(task.item.id, "subtask", "Tokenise the input", maps_to="US1")
    await svc.add_block(task.item.id, "subtask", "Parse the operators")
    review = await create_item(svc, "review", "Review the query parser")
    await svc.add_block(
        review.item.id, "finding", "Unbounded recursion", fields={"severity": "High"}
    )
    severity = svc.field_default("finding", "severity")
    assert severity is not None
    await svc.add_block(
        review.item.id, "finding", "Misleading error text", fields={"severity": severity}
    )


def init_populated(root: Path) -> None:
    """The `minimal` squad plus a feature with two stories, a task under it with two subtasks
    (the first mapped to the first story) and a review with two findings."""
    init_minimal(root)
    asyncio.run(_populate(root))
