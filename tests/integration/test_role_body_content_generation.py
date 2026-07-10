"""Generated role-body content (``sq role <slug> show`` reads this back): the body lists the
role's own skills, carries the two-regime operating contract, a reviewer's body carries the
findings-agreement clause (and a non-reviewer's does not), a comment-scoping pointer names the
convention by pointing at the squads skill rather than restating it, the product-owner's body
cites a real (not illustrative-only) ``add-story`` command, and ``sync`` regenerates a
corrupted role body in place.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_role_body_lists_the_roles_own_skills(svc):
    item = await svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "## Skills" in body
    assert "`sq-guide`" in body


async def test_role_body_carries_the_two_regime_operating_contract(svc):
    item = await svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "follow your `sq-<type>` skill" in body
    assert "### Spawned as a subagent" in body
    assert "### Live with the operator" in body
    assert "Record what the next reader needs, when it becomes true" in body
    assert "full record" in body
    assert "when work actually moves" in body


async def test_reviewers_body_carries_the_findings_agreement_a_non_reviewer_does_not(svc):
    reviewer = await svc.activate_role("reviewer")
    reviewer_body = svc.paths.abspath(reviewer.path).read_text(encoding="utf-8")
    assert "add-finding" in reviewer_body
    assert "never as body prose" in reviewer_body

    writer = await svc.activate_role("tech-writer")
    writer_body = svc.paths.abspath(writer.path).read_text(encoding="utf-8")
    assert "add-finding" not in writer_body
    assert "never as body prose" not in writer_body


async def test_role_body_has_a_comment_scoping_pointer_not_a_restatement(svc):
    item = await svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "comment-scoping" in body
    assert "squads" in body  # points at the squads skill by name


async def test_product_owner_body_cites_the_real_add_story_command(svc):
    item = await svc.activate_role("product-owner")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "sq story add" not in body  # not a real command
    assert "sq feature <n> add-story" in body


async def test_sync_regenerates_a_corrupted_role_body_in_place(svc):
    from squads import _sections as sections
    from squads._models import _markers as markers

    item = await svc.activate_role("qa")
    path = svc.paths.abspath(item.path)
    corrupted = sections.replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "\n_corrupted_\n"
    )
    path.write_text(corrupted, encoding="utf-8")
    assert "Spawned as a subagent" not in path.read_text(encoding="utf-8")

    await svc.sync()
    restored = path.read_text(encoding="utf-8")
    assert "### Spawned as a subagent" in restored
    assert "### Live with the operator" in restored
    assert "Record what the next reader needs, when it becomes true" in restored
