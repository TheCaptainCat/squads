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


def init_override_populated(root: Path) -> None:
    """The `minimal` squad under the override test vocabulary: an initiative with two outcomes, a
    job under it with two actions (the second deferred) and a record."""
    init_overridden(root, OVERRIDE)
    asyncio.run(_populate(root))
