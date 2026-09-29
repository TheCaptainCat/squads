"""Setting a body over prose someone already wrote is refused on every door that sets rather
than appends. The distinction is authored vs. unwritten, not empty vs. non-empty, so a fresh
template scaffold or sub-entity placeholder is never mistaken for authored content."""

import pytest

from _helpers import create_item
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

# Every bundled item type that renders a body scaffold: the dedicated per-type templates plus a
# custom type, which falls back to `items/_default.md.j2` and interpolates its own type name.
_SCAFFOLDED_TYPES = ["task", "feature", "epic", "bug", "decision", "review", "guide"]

_KINDS = [("feature", "story", "US1"), ("task", "subtask", "ST1"), ("review", "finding", "F1")]


# --------------------------------------------------------------------- unwritten bodies pass


@pytest.mark.parametrize("item_type", _SCAFFOLDED_TYPES)
async def test_a_first_write_over_a_type_s_own_template_scaffold_is_not_a_replacement(
    svc, item_type
):
    item = (await create_item(svc, item_type, "t")).item
    assert await svc.read_body(item.id) != ""

    await svc.set_body(item.id, "the first real prose")
    assert await svc.read_body(item.id) == "the first real prose"


async def test_a_first_write_over_a_custom_skill_s_scaffold_is_not_a_replacement(svc):
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    assert await svc.read_body(skill.id) != ""

    await svc.set_body(skill.id, "## Instructions\n\nCut the branch, then tag.")
    assert (await svc.read_body(skill.id)).startswith("## Instructions")


@pytest.mark.parametrize(("parent_type", "kind", "local_id"), _KINDS)
async def test_a_first_write_over_a_sub_entity_placeholder_is_not_a_replacement(
    svc, parent_type, kind, local_id
):
    parent = (await create_item(svc, parent_type, "p")).item
    await svc.add_block(parent.id, kind, "a block")
    assert (await svc.get_block(parent.id, kind, local_id)).body.strip() != ""

    await svc.set_block_body(parent.id, kind, local_id, "the first real prose", append=False)
    assert (await svc.get_block(parent.id, kind, local_id)).body.strip() == "the first real prose"


# ------------------------------------------------------------------- authored bodies refuse


@pytest.mark.parametrize("item_type", _SCAFFOLDED_TYPES)
async def test_replacing_prose_written_earlier_is_refused_and_writes_nothing(svc, item_type):
    item = (await create_item(svc, item_type, "t")).item
    await svc.set_body(item.id, "## Runbook\n\nline two\nline three")
    path = svc.paths.abspath((await svc.get(item.id)).path)
    before = path.read_text(encoding="utf-8")

    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_body(item.id, "probe")

    assert path.read_text(encoding="utf-8") == before


async def test_a_body_supplied_at_create_time_counts_as_authored(svc):
    """A body supplied at create time, which never renders a scaffold, still counts as authored."""
    item = (await create_item(svc, "task", "t", body="prose handed in at create time")).item

    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_body(item.id, "probe")
    assert await svc.read_body(item.id) == "prose handed in at create time"


async def test_replacing_an_authored_custom_skill_body_is_refused(svc):
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    await svc.set_body(skill.id, "## Instructions\n\nCut the branch, then tag.")

    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_body(skill.id, "probe")
    assert (await svc.read_body(skill.id)).startswith("## Instructions")


@pytest.mark.parametrize(("parent_type", "kind", "local_id"), _KINDS)
async def test_replacing_an_authored_sub_entity_body_is_refused(svc, parent_type, kind, local_id):
    parent = (await create_item(svc, parent_type, "p")).item
    await svc.add_block(parent.id, kind, "a block", body="prose worth keeping")

    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_block_body(parent.id, kind, local_id, "probe", append=False)
    assert (await svc.get_block(parent.id, kind, local_id)).body.strip() == "prose worth keeping"


# --------------------------------------------------------------------------- the way through


async def test_the_refusal_names_the_size_and_shows_what_would_be_discarded(svc):
    item = (await create_item(svc, "task", "t")).item
    await svc.set_body(item.id, "## Runbook\nline two\nline three\nline four\nline five")

    with pytest.raises(SquadsError) as excinfo:
        await svc.set_body(item.id, "probe")
    message = str(excinfo.value)

    assert "5 lines" in message
    assert "## Runbook" in message
    assert "2 more lines" in message
    assert "--append" in message and "--force" in message


async def test_the_refusal_on_a_seeded_view_host_counts_only_the_authored_prose(svc):
    """The refusal's preview counts only the authored prose, never a seeded view's own tag."""
    item = (await create_item(svc, "milestone", "M")).item
    await svc.set_body(item.id, "hello")
    await svc.set_body(item.id, "appended", append=True)

    with pytest.raises(SquadsError) as excinfo:
        await svc.set_body(item.id, "probe")
    message = str(excinfo.value)

    assert "3 lines" in message
    assert "hello" in message
    assert "appended" in message
    assert "more line" not in message
    assert "sq:view" not in message


async def test_append_is_never_guarded_because_it_destroys_nothing(svc):
    item = (await create_item(svc, "task", "t")).item
    await svc.set_body(item.id, "first")
    await svc.set_body(item.id, "second", append=True)
    assert await svc.read_body(item.id) == "first\n\nsecond"


async def test_force_replaces_an_authored_body(svc):
    item = (await create_item(svc, "task", "t")).item
    await svc.set_body(item.id, "first")
    await svc.set_body(item.id, "second", force=True)
    assert await svc.read_body(item.id) == "second"


async def test_force_replaces_an_authored_sub_entity_body(svc):
    parent = (await create_item(svc, "task", "p")).item
    await svc.add_block(parent.id, "subtask", "a block", body="prose")
    await svc.set_block_body(parent.id, "subtask", "ST1", "rewritten", append=False, force=True)
    assert (await svc.get_block(parent.id, "subtask", "ST1")).body.strip() == "rewritten"


async def test_a_forced_replacement_records_what_it_discarded_in_the_reflog(svc):
    item = (await create_item(svc, "task", "t")).item
    await svc.set_body(item.id, "one\ntwo\nthree")
    await svc.set_body(item.id, "replacement", force=True)

    body_lines = [ln for ln in await svc.read_reflog() if ln.op == "body"]
    assert [ln.delta.get("replaced_lines") for ln in body_lines] == [None, 3]
