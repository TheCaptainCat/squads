"""The rendered role definition — the text ``sq role <slug> show`` produces fresh on every
call, and the only place that text exists: nothing stores it. It no longer lists the role's own
skills, it carries the two-regime operating contract, a reviewer's definition carries the
findings-agreement clause (and a non-reviewer's does not), a comment-scoping pointer names the
convention by pointing at the squads skill rather than restating it, and the product-owner's
cites a real (not illustrative-only) ``add-story`` command.

Every assertion reads the *rendered* definition, never the item's file. Activation writes an
empty ``sq:body`` region and no write path ever fills it, so reading the file would be
answering a question about storage while claiming to answer one about content.
"""

import pytest

pytestmark = pytest.mark.anyio


async def _definition(svc, slug: str) -> str:
    """The role's definition as an agent reads it: resolved on the call, rendered on the call."""
    from squads._roles._resolver import resolve_role_for_item

    item = await svc.activate_role(slug)
    return svc.role_definition_text(resolve_role_for_item(item, svc.paths.squad_dir))


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


async def test_activation_writes_an_empty_body_region_and_keeps_its_markers(svc):
    """No write path stores the definition. The region is emptied rather than removed: an
    absent one is a different fact about an item file, and the marker pair is the shape every
    item file shares."""
    from squads import _sections as sections
    from squads._models import _markers as markers

    item = await svc.activate_role("qa")
    text = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert sections.has_section(text, markers.BODY)
    assert not (sections.get_section(text, markers.BODY) or "").strip()


async def test_sync_no_longer_touches_a_corrupted_role_body(svc):
    """The producer inverted to read time: nothing writes a role's ``sq:body`` region any
    more, so a corrupted stored body is not a defect ``sq sync`` heals. ``sq role <slug>
    show`` still renders the correct definition regardless — it never reads the region."""
    from squads import _sections as sections
    from squads._models import _markers as markers
    from squads._roles._resolver import resolve_role_for_item

    item = await svc.activate_role("qa")
    path = svc.paths.abspath(item.path)
    corrupted = sections.replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "\n_corrupted_\n"
    )
    path.write_text(corrupted, encoding="utf-8")
    assert "Spawned as a subagent" not in path.read_text(encoding="utf-8")

    await svc.sync()
    on_disk = path.read_text(encoding="utf-8")
    assert "_corrupted_" in on_disk  # sync leaves the region untouched, corruption and all
    assert "### Spawned as a subagent" not in on_disk

    definition = svc.role_definition_text(resolve_role_for_item(item, svc.paths.squad_dir))
    assert "### Spawned as a subagent" in definition
    assert "### Live with the operator" in definition
    assert "Record what the next reader needs, when it becomes true" in definition
