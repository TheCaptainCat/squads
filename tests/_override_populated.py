"""The populated override squad the surface tests share: items of the vocabulary that
`tests/fixtures/override_squad/workflow.toml` declares, with none of the bundled work vocabulary.

The counter starts after the squad's role and its seeded skills, so the numbers below are fixed.
"""

import asyncio
from pathlib import Path

from squads._workflow._loader import load_workflow_spec
from tests._helpers import create_item, make_service
from tests._squads import init_overridden, paths_of

OVERRIDE = Path(__file__).parent / "fixtures" / "override_squad"

INITIATIVE = 8
JOB = 9
RECORD = 10


async def _populate(root: Path) -> None:
    paths = paths_of(root)
    svc = make_service(paths, spec=load_workflow_spec(paths.squad_dir))
    initiative = await create_item(
        svc,
        "initiative",
        "Open the beta",
        fields={"urgency": "Now"},
        attributes={"horizon": "2026-12-01", "themes": ["growth"]},
    )
    await svc.add_block(
        initiative.item.id, "outcome", "Fifty active teams", body="Measured weekly."
    )
    await svc.add_block(initiative.item.id, "outcome", "A published roadmap", body="Public.")
    job = await create_item(
        svc,
        "job",
        "Write the onboarding guide",
        parent=initiative.item.id,
        fields={"work_size": "M"},
        attributes={"owner_team": "docs", "needs_review": True},
    )
    record = await create_item(svc, "record", "Pick the hosting plan")
    await svc.add_block(
        job.item.id, "action", "Draft the outline", fields={"impact": "Large"}, body="Outline."
    )
    await svc.add_block(
        job.item.id,
        "action",
        "Record the walkthrough",
        status="Deferred",
        deferred_to=record.item.id,
        body="Moved to the hosting record.",
    )


async def _populate_surface(root: Path) -> None:
    paths = paths_of(root)
    svc = make_service(paths, spec=load_workflow_spec(paths.squad_dir))
    initiative = await create_item(svc, "initiative", "Search")
    await svc.add_block(initiative.item.id, "outcome", "Query the index")
    await svc.add_block(initiative.item.id, "outcome", "Rank the results")
    job = await create_item(svc, "job", "Build the query parser", parent=initiative.item.id)
    await svc.add_block(job.item.id, "action", "Tokenise the input", maps_to="OC1")
    await svc.add_block(job.item.id, "action", "Parse the operators")
    third = await create_item(svc, "job", "Review the query parser", parent=initiative.item.id)
    await svc.add_block(third.item.id, "action", "Unbounded recursion", fields={"impact": "large"})
    await svc.add_block(third.item.id, "action", "Misleading error text")


def init_override_surface(root: Path) -> None:
    """The counterpart of the bundled populated squad: an initiative with two outcomes, a job under
    it with two actions (the first mapped to the first outcome) and a second job with two actions,
    the first carrying the field. The counter starts at the same numbers."""
    init_overridden(root, OVERRIDE, seed_skills=False)
    asyncio.run(_populate_surface(root))


def init_override_populated(root: Path) -> None:
    """The `minimal` squad under the override test vocabulary: an initiative with two outcomes, a
    job under it with two actions (the second deferred) and a record."""
    init_overridden(root, OVERRIDE)
    asyncio.run(_populate(root))
