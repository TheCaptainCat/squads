"""The rendered role definition — the text ``sq role <slug> show`` produces on every read,
computed fresh from a ``sq:view:role_definition`` tag on every call, never a stored copy. It no
longer lists the role's own skills, it carries the two-regime operating contract, a reviewer's
definition carries the findings-agreement clause (and a non-reviewer's does not), a
comment-scoping pointer names the convention by pointing at the squads skill rather than
restating it, and the product-owner's cites a real (not illustrative-only) ``add-story``
command.

Every assertion reads the *rendered* definition (``svc.read_body``, the same body-read boundary
``sq role <slug> show`` goes through), never the item's file directly. Activation seeds the tag
into ``sq:body``; no write path ever stores the definition text itself, so the file still holds
nothing the resolver's answer could go stale against.
"""

import pytest

pytestmark = pytest.mark.anyio


async def _definition(svc, slug: str) -> str:
    """The role's definition as an agent reads it: resolved and rendered fresh on the call,
    off the tag ``sq:body`` carries — the same read every other item's body goes through."""
    item = await svc.activate_role(slug)
    return await svc.read_body(item.id)


async def test_role_body_no_longer_lists_the_roles_own_skills(svc):
    """The resolved skills list left the body for the computed catalog card (``sq role <slug>
    show``'s ``skills:`` row) — the body carries neither the heading nor the list, though the
    list itself is still resolvable live."""
    definition = await _definition(svc, "tech-writer")
    assert "## Skills" not in definition
    assert "`sq-guide`" not in definition
    assert "sq-guide" in await svc.resolved_skills_for_role("tech-writer")


async def test_role_body_carries_the_two_regime_operating_contract(svc):
    definition = await _definition(svc, "tech-writer")
    assert "follow your `sq-<type>` skill" in definition
    assert "### Spawned as a subagent" in definition
    assert "### Live with the operator" in definition
    assert "Record what the next reader needs, when it becomes true" in definition
    assert "full record" in definition
    assert "when work actually moves" in definition


async def test_reviewers_body_carries_the_findings_agreement_a_non_reviewer_does_not(svc):
    reviewer_definition = await _definition(svc, "reviewer")
    assert "add-finding" in reviewer_definition
    assert "never as body prose" in reviewer_definition

    writer_definition = await _definition(svc, "tech-writer")
    assert "add-finding" not in writer_definition
    assert "never as body prose" not in writer_definition


async def test_role_body_has_a_comment_scoping_pointer_not_a_restatement(svc):
    definition = await _definition(svc, "tech-writer")
    assert "comment-scoping" in definition
    assert "squads" in definition  # points at the squads skill by name


async def test_product_owner_body_cites_the_real_add_story_command(svc):
    definition = await _definition(svc, "product-owner")
    assert "sq story add" not in definition  # not a real command
    assert "sq feature <n> add-story" in definition


async def test_role_body_no_longer_carries_the_startup_command_set(svc):
    """The slug-bound startup commands (`sq memory <slug> list`, `sq board list`, `sq mine
    <slug>`, `sq inbox <slug>`) moved to the agent pointer, which is what an agent actually
    reads first — the role body is not a second slug-bound copy of the same set. The generic,
    non-slug-bound form of this protocol still ships once, in CLAUDE.md's managed section."""
    definition = await _definition(svc, "qa")
    assert "sq memory qa list" not in definition
    assert "sq board list" not in definition
    assert "sq mine qa" not in definition
    assert "sq inbox qa" not in definition
    # the rest of the working-agreements line stays
    assert "Operate as **Mara Tester**" in definition


async def test_activation_seeds_the_placement_tag_and_keeps_the_bodys_markers(svc):
    """No write path stores the definition itself. The region carries exactly the
    ``sq:view:role_definition`` placement tag rather than being emptied — content-free by
    design (see ``squads._models._markers.VIEW``), so there is still nothing here that can go
    stale against the resolved definition."""
    from squads import _sections as sections
    from squads._models import _markers as markers

    item = await svc.activate_role("qa")
    text = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert sections.has_section(text, markers.BODY)
    region = (sections.get_section(text, markers.BODY) or "").strip()
    assert region == markers.open_marker(markers.view_tag("role_definition"))


async def test_a_role_body_with_no_tag_at_all_reads_literally_not_as_the_definition(svc):
    """A role's definition renders off the tag its own ``sq:body`` carries, made explicit
    rather than left implicit: a body carrying no ``sq:view:<name>`` tag (corruption, or a
    squad pre-dating this tag entirely) reads back literally — the same "leave it as-is, let
    `sq check`/`sq repair` be the reporting and healing surfaces" contract every other item's
    body already has. See ``tests/service/test_repair_strips_only_retired_regions.py``'s
    ``test_a_role_body_converges_onto_the_placement_tag_and_keeps_its_markers`` for the healing
    half — the repair sweep is what converges a body in this shape back onto the tag."""
    from squads import _sections as sections
    from squads._models import _markers as markers

    item = await svc.activate_role("qa")
    path = svc.paths.abspath(item.path)
    corrupted = sections.replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "\n_corrupted_\n"
    )
    path.write_text(corrupted, encoding="utf-8")

    await svc.sync()
    on_disk = path.read_text(encoding="utf-8")
    assert "_corrupted_" in on_disk  # sync leaves the region untouched, corruption and all

    definition = await svc.read_body(item.id)
    assert definition == "_corrupted_"
    assert "### Spawned as a subagent" not in definition
