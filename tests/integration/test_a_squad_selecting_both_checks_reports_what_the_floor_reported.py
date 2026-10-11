"""The whole-squad comparison: one squad with an offender and a clean neighbour for every input
shape of the two checks that are selected rather than always on (a status banner in a body or
a description on each type that can carry one; a sub-entity title one over and exactly at the
threshold on each hosting type). Under the bundled spec nothing selects either check, so the
squad reports nothing; under this repository's own workflow override, which selects both, it
reports exactly the list below -- the list the engine produced before either check became
selectable.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._services import _service as service

pytestmark = pytest.mark.anyio

REPO_OVERRIDE = Path(__file__).resolve().parents[2] / "squads" / ".overrides" / "workflow.toml"

OVER = "T" * 121
AT = "T" * 120
BANNER = "STATUS: Proposed"
MENTION = "Describes the Draft to Ready transition this work builds."
WRITTEN = "Written."

BODY_BANNER = (
    "body opens with a status/lifecycle banner"
    " — move state to frontmatter or a dated discussion comment"
)
DESCRIPTION_BANNER = (
    "description opens with a status/lifecycle banner"
    " — move state to frontmatter or a dated discussion comment"
)
#: (level, item id, message) in the order ``check()`` returns them.
EXPECTED: list[tuple[str, str, str]] = [
    ("warn", "EPIC-2", BODY_BANNER),
    ("warn", "EPIC-3", DESCRIPTION_BANNER),
    ("warn", "FEAT-5", BODY_BANNER),
    ("warn", "FEAT-6", DESCRIPTION_BANNER),
    ("warn", "TASK-8", BODY_BANNER),
    ("warn", "TASK-9", DESCRIPTION_BANNER),
    ("warn", "BUG-11", BODY_BANNER),
    ("warn", "BUG-12", DESCRIPTION_BANNER),
    ("warn", "ADR-14", BODY_BANNER),
    ("warn", "ADR-15", DESCRIPTION_BANNER),
    ("warn", "PRD-17", BODY_BANNER),
    ("warn", "PRD-18", DESCRIPTION_BANNER),
    ("warn", "MILE-20", BODY_BANNER),
    ("warn", "MILE-21", DESCRIPTION_BANNER),
    ("warn", "GUIDE-23", BODY_BANNER),
    ("warn", "GUIDE-24", DESCRIPTION_BANNER),
    ("warn", "SKILL-26", BODY_BANNER),
    ("warn", "SKILL-27", DESCRIPTION_BANNER),
    ("warn", "OP-29", BODY_BANNER),
    ("warn", "OP-30", DESCRIPTION_BANNER),
    ("warn", "ROLE-32", DESCRIPTION_BANNER),
    (
        "warn",
        "FEAT-33",
        (
            "advisory: story US1 title is 121 chars (threshold: 120)"
            " — a sub-entity title is a one-line handle; put the detail in the body"
        ),
    ),
    (
        "warn",
        "TASK-34",
        (
            "advisory: subtask ST1 title is 121 chars (threshold: 120)"
            " — a sub-entity title is a one-line handle; put the detail in the body"
        ),
    ),
    (
        "warn",
        "REV-35",
        (
            "advisory: finding F1 title is 121 chars (threshold: 120)"
            " — a sub-entity title is a one-line handle; put the detail in the body"
        ),
    ),
]


async def _populate(svc: service.Service) -> None:
    """One banner-in-body, one banner-in-description and one clean item per bundled type that
    carries free text, then a story, a subtask and a finding at 121 and at 120 characters."""
    for item_type in ("epic", "feature", "task", "bug", "decision", "contract", "milestone"):
        body_banner = (await create_item(svc, item_type, f"{item_type} body banner")).item
        await svc.set_body(body_banner.id, BANNER)
        desc_banner = (await create_item(svc, item_type, f"{item_type} description banner")).item
        await svc.update(desc_banner.id, description=BANNER)
        clean = (await create_item(svc, item_type, f"{item_type} clean")).item
        await svc.set_body(clean.id, MENTION)
    guide_body = (await create_item(svc, "guide", "guide body banner")).item
    await svc.set_body(guide_body.id, "## Status\n\nDrafted.")
    guide_desc = (await create_item(svc, "guide", "guide description banner")).item
    await svc.update(guide_desc.id, description=BANNER)
    guide_clean = (await create_item(svc, "guide", "guide clean")).item
    await svc.set_body(guide_clean.id, MENTION)
    for slug, item_type in (("skill-a", "skill"), ("op-a", "operator")):
        body_banner = (await create_item(svc, item_type, f"{item_type} body", slug=slug)).item
        await svc.set_body(body_banner.id, "**Status:** Draft")
        desc_banner = (
            await create_item(svc, item_type, f"{item_type} description", slug=f"{slug}-d")
        ).item
        await svc.update(desc_banner.id, description=BANNER)
        clean = (await create_item(svc, item_type, f"{item_type} clean", slug=f"{slug}-c")).item
        await svc.set_body(clean.id, MENTION)
    role = (await create_item(svc, "role", "role description", slug="role-a")).item
    await svc.update(role.id, description=BANNER)

    feature = (await create_item(svc, "feature", "feature hosting stories")).item
    await svc.add_story(feature.id, OVER, body=WRITTEN)
    await svc.add_story(feature.id, AT, body=WRITTEN)
    task = (await create_item(svc, "task", "task hosting subtasks")).item
    await svc.add_subtask(task.id, OVER, body=WRITTEN)
    await svc.add_subtask(task.id, AT, body=WRITTEN)
    review = (await create_item(svc, "review", "review hosting findings")).item
    await svc.add_finding(review.id, OVER, body=WRITTEN)
    await svc.add_finding(review.id, AT, body=WRITTEN)


def _with_repo_override(svc: service.Service) -> service.Service:
    override_dir = svc.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    text = REPO_OVERRIDE.read_text(encoding="utf-8")
    assert text.startswith(f"# squads:override-base:{__version__}\n")
    (override_dir / "workflow.toml").write_text(text, encoding="utf-8")
    return service.open_service()


def _report(issues) -> list[tuple[str, str, str]]:
    return [(i.level, i.item, i.message) for i in issues]


async def test_the_squad_reports_the_recorded_list_when_both_checks_are_selected(svc) -> None:
    await _populate(svc)
    selecting = _with_repo_override(svc)
    assert _report(await selecting.check()) == EXPECTED


async def test_the_same_squad_reports_nothing_when_neither_check_is_selected(svc) -> None:
    await _populate(svc)
    assert _report(await svc.check()) == []
