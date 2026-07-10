"""Schema 0.5 -> 0.7 migration: unpad frontmatter id/parent/refs and body-prose id mentions —
while leaving fenced/inline code spans and filename references (which are never renamed) alone.
"""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _v0_5_to_v0_7
from squads._models._item import DEFAULT_ID_PADDING, format_item_id

pytestmark = pytest.mark.anyio


def _pad(item_id: str) -> str:
    prefix, _, digits = item_id.rpartition("-")
    return format_item_id(prefix, int(digits), DEFAULT_ID_PADDING)


async def _devolve_to_padded(
    svc, item_id: str, *, parent: str | None, refs: list[str], subentity_title: str | None = None
) -> None:
    """Rewrite one item's frontmatter id/parent/refs (and, optionally, its first sub-entity's
    title) back to the pre-migration padded form. Must be the LAST write before migrating: any
    later service-layer mutation re-serializes frontmatter from the index and would re-unpad it."""
    item = await svc.get(item_id)
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    fm["id"] = _pad(item_id)
    if parent:
        fm["parent"] = _pad(parent)
    if refs:
        fm["refs"] = [_pad(r) for r in refs]
    if subentity_title is not None:
        fm["subentities"][0]["title"] = subentity_title
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def test_migration_unpads_frontmatter_and_prose_but_skips_code_spans_and_filenames(svc):
    feature = (await svc.create("feature", "Login")).item
    bug = (await svc.create("bug", "Session leak")).item
    task = (await svc.create("task", "Implement auth", parent=feature.id, refs=[bug.id])).item
    await svc.add_subtask(task.id, "placeholder")
    await svc.set_subtask_body(task.id, "ST1", "Real subtask description, not the stub.")

    padded_feature_id = _pad(feature.id)
    padded_bug_id = _pad(bug.id)
    bug_filename = svc.paths.abspath(bug.path).name

    # Set the body BEFORE devolving to padded (set_body re-serializes frontmatter from the
    # index-backed item, which would silently re-unpad everything devolved below).
    body = (
        f"See {padded_feature_id} for context, and {padded_bug_id} for the underlying bug.\n\n"
        "```text\n"
        f"example id: {padded_feature_id}\n"
        "```\n\n"
        f"Inline example: `{padded_bug_id}` should stay padded.\n\n"
        f"Filed against {bug_filename} — that reference must survive verbatim.\n"
    )
    await svc.set_body(task.id, body)

    await _devolve_to_padded(svc, feature.id, parent=None, refs=[])
    await _devolve_to_padded(svc, bug.id, parent=None, refs=[])
    await _devolve_to_padded(
        svc,
        task.id,
        parent=feature.id,
        refs=[bug.id],
        subentity_title=f"tie into {padded_feature_id} contract",
    )

    task_path = svc.paths.abspath((await svc.get(task.id)).path)
    task_filename_before = task_path.name

    changed = _v0_5_to_v0_7.migrate(svc.paths)
    assert changed == 3

    feat_fm = read_frontmatter(svc.paths.abspath((await svc.get(feature.id)).path))
    bug_fm = read_frontmatter(svc.paths.abspath((await svc.get(bug.id)).path))
    task_fm = read_frontmatter(task_path)
    assert feat_fm["id"] == feature.id
    assert bug_fm["id"] == bug.id
    assert task_fm["id"] == task.id
    assert task_fm["parent"] == feature.id
    assert task_fm["refs"] == [bug.id]
    assert task_fm["subentities"][0]["title"] == f"tie into {feature.id} contract"

    final_body = sections.split_frontmatter(task_path.read_text(encoding="utf-8"))[1]
    assert f"See {feature.id} for context" in final_body
    assert f"and {bug.id} for the underlying bug" in final_body
    assert f"example id: {padded_feature_id}" in final_body  # fenced block: untouched
    assert f"`{padded_bug_id}`" in final_body  # inline code span: untouched
    assert f"Filed against {bug_filename}" in final_body  # filename reference: untouched
    assert padded_feature_id not in final_body.split("```")[0].split("Filed against")[0]

    assert task_path.name == task_filename_before  # filenames are never touched
    assert (svc.paths.abspath(bug.path).parent / bug_filename).is_file()

    assert (await svc.get(task_fm["parent"])).id == feature.id
    assert (await svc.get(task_fm["refs"][0])).id == bug.id
    issues = await svc.check()
    assert not issues

    assert _v0_5_to_v0_7.migrate(svc.paths) == 0  # idempotent
