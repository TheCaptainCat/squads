"""``Service.set_body`` replaces by default, appends with a blank-line separator, and is
rejected outright, even with ``--force``, for a role or system skill — unless the view is
dropped from ``[selected]``. A custom skill carries no such classification."""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def test_set_body_replaces_by_default_and_appends_with_a_blank_line_separator(svc):
    task = (await create_item(svc, "task", "t", description="summary stays in frontmatter")).item

    await svc.set_body(task.id, "## Description\n\nFull body content.")
    assert await svc.read_body(task.id) == "## Description\n\nFull body content."
    assert (await svc.get(task.id)).description == "summary stays in frontmatter"

    await svc.set_body(task.id, "More detail.", append=True)
    assert (await svc.read_body(task.id)).endswith("Full body content.\n\nMore detail.")


async def test_set_body_on_a_role_is_rejected(svc):
    role = await svc.get("ROLE-000001")
    with pytest.raises(SquadsError, match="renders through its declared sq:view:") as exc:
        await svc.set_body("ROLE-000001", "free-form body")
    assert "roles.toml" in str(exc.value)
    assert role.slug


async def test_set_body_on_a_role_is_rejected_even_with_force(svc):
    """The roster refusal never consults ``force``."""
    with pytest.raises(SquadsError, match="`--force` does not lift this"):
        await svc.set_body("ROLE-000001", "free-form body", force=True)


async def test_append_on_a_role_is_rejected_the_same_way_as_replace(svc):
    with pytest.raises(SquadsError, match="renders through its declared sq:view:") as exc:
        await svc.set_body("ROLE-000001", "free-form body", append=True)
    assert "roles.toml" in str(exc.value)


async def test_set_body_on_a_system_skill_is_rejected(svc):
    seeded = await svc.seed_bundled_skills()
    with pytest.raises(SquadsError, match="renders through its declared sq:view:") as exc:
        await svc.set_body(seeded[0].id, "free-form body")
    assert "view template override" in str(exc.value)


async def test_append_on_a_system_skill_is_rejected_the_same_way_as_replace(svc):
    seeded = await svc.seed_bundled_skills()
    with pytest.raises(SquadsError, match="renders through its declared sq:view:") as exc:
        await svc.set_body(seeded[0].id, "free-form body", append=True)
    assert "view template override" in str(exc.value)


@pytest.mark.parametrize(
    ("slug", "expected", "unexpected"),
    [
        pytest.param(
            "greeting",
            "its `.overrides/templates/views/greeting_skill.md.j2` view template override",
            "playbook.toml",
            id="self-sourced-permanently-system",
        ),
        pytest.param(
            "sq-memory",
            "its `.overrides/templates/views/memory_skill.md.j2` view template override",
            "playbook.toml",
            id="self-sourced-permanently-system-2",
        ),
        pytest.param(
            "squads",
            "`.overrides/playbook.toml`",
            "[types.",
            id="playbook-sourced-no-type-lane",
        ),
        pytest.param(
            "sq-bug",
            "the `[types.bug]` lane in `.overrides/playbook.toml`",
            "view template override",
            id="playbook-sourced-per-item-type-lane",
        ),
    ],
)
async def test_a_system_skills_refusal_names_its_own_real_authoring_surface(
    svc, slug, expected, unexpected
):
    """A system skill's refusal names its own real authoring surface, never a generic
    "this type's lane" claim that does not apply to it."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", slug)
    assert skill is not None
    with pytest.raises(SquadsError, match="renders through its declared sq:view:") as exc:
        await svc.set_body(skill.id, "free-form body")
    assert expected in str(exc.value), str(exc.value)
    assert unexpected not in str(exc.value), str(exc.value)


async def test_a_role_with_its_view_dropped_admits_replace_and_append(svc):
    """Dropping the view from ``[selected]`` admits an ordinary authored write, preserving the
    role's existing tag rather than stripping it."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")

    _write_override(svc.paths.squad_dir, '[selected]\nviews = ["milestone_rollup"]\n')
    dropped = service.Service(svc.paths, spec=load_workflow_spec(squad_dir=svc.paths.squad_dir))

    await dropped.set_body(role.id, "free-form body")
    body = await dropped.read_body(role.id)
    assert body.startswith("free-form body")
    assert "<!-- sq:view:role_definition -->" in body

    await dropped.set_body(role.id, "more.", append=True)
    assert "free-form body\n\nmore." in await dropped.read_body(role.id)


async def test_set_body_on_a_custom_skill_is_authored_and_re_editable(svc):
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")

    await svc.set_body(skill.id, "## Instructions\n\nCut the branch, then tag.")
    assert await svc.read_body(skill.id) == "## Instructions\n\nCut the branch, then tag."

    await svc.set_body(skill.id, "Then publish.", append=True)
    assert (await svc.read_body(skill.id)).endswith("tag.\n\nThen publish.")
