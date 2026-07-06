"""Schema 0.5 -> 0.7 migration: unpad frontmatter id/refs/parent and body-prose ID mentions."""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _v0_5_to_v0_7
from squads._models._enums import ItemType
from squads._models._item import DEFAULT_ID_PADDING, format_item_id

pytestmark = pytest.mark.anyio


def _pad(item_id: str) -> str:
    """Reformat an already-unpadded id (as `svc.create` writes today) to its old padded form."""
    prefix, _, digits = item_id.rpartition("-")
    return format_item_id(prefix, int(digits), DEFAULT_ID_PADDING)


async def _devolve_to_padded(
    svc, item_id: str, *, parent: str | None, refs: list[str], subentity_title: str | None = None
) -> None:
    """Hand-rewrite one item's frontmatter id/parent/refs (and, optionally, its first
    sub-entity's title) back to the pre-migration padded form (what a pre-0.7 squad has on disk
    today), leaving `sequence_id` — and the file's own already-padded filename — untouched.

    This must be the *last* write to the file before running the migration: any further
    service-layer mutation (e.g. `set_body`) re-serializes the whole frontmatter from the
    index-backed `Item`, which would silently re-unpad everything devolved here.
    """
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


async def test_migrate_unpads_frontmatter_refs_and_prose_but_skips_code_spans(svc):
    feature = (await svc.create(ItemType.FEATURE, "Login")).item
    bug = (await svc.create(ItemType.BUG, "Session leak")).item
    task = (
        await svc.create(ItemType.TASK, "Implement auth", parent=feature.id, refs=[bug.id])
    ).item
    await svc.add_subtask(task.id, "placeholder")  # ST1 — retitled (padded mention) below
    await svc.set_subtask_body(task.id, "ST1", "Real subtask description, not the stub.")

    padded_feature_id = _pad(feature.id)
    padded_bug_id = _pad(bug.id)
    bug_filename = svc.paths.abspath(bug.path).name  # e.g. "BUG-000002-session-leak.md"

    # A mention-heavy body: a real prose mention (must unpad), a fenced code block and an inline
    # code span (both must be left exactly as written — a literal example, not a mention), and a
    # filename reference citing the padded id as a path stem (must stay padded — that file, on
    # disk, is never renamed). Set it *before* devolving to padded (see the note on
    # `_devolve_to_padded`): `set_body` re-serializes frontmatter from the index-backed item.
    body = (
        f"See {padded_feature_id} for context, and {padded_bug_id} for the underlying bug.\n\n"
        "```text\n"
        f"example id: {padded_feature_id}\n"
        "```\n\n"
        f"Inline example: `{padded_bug_id}` should stay padded.\n\n"
        f"Filed against {bug_filename} — that reference must survive verbatim.\n"
    )
    await svc.set_body(task.id, body)

    # Devolve all three files to the pre-0.7 padded on-disk shape — last write before migrating.
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
    assert changed == 3  # feature, bug, task — every file we devolved

    # --- structural: frontmatter id/parent/refs are unpadded everywhere ---
    feat_fm = read_frontmatter(svc.paths.abspath((await svc.get(feature.id)).path))
    bug_fm = read_frontmatter(svc.paths.abspath((await svc.get(bug.id)).path))
    task_fm = read_frontmatter(task_path)
    assert feat_fm["id"] == feature.id
    assert bug_fm["id"] == bug.id
    assert task_fm["id"] == task.id
    assert task_fm["parent"] == feature.id
    assert task_fm["refs"] == [bug.id]

    # --- sub-entity title mention is unpadded too ---
    assert task_fm["subentities"][0]["title"] == f"tie into {feature.id} contract"

    # --- prose: the real mention is rewritten, fenced/inline code is left untouched, and the
    # filename reference is left byte-identical (the file it names is never renamed) ---
    final_body = sections.split_frontmatter(task_path.read_text(encoding="utf-8"))[1]
    assert f"See {feature.id} for context" in final_body
    assert f"and {bug.id} for the underlying bug" in final_body
    assert f"example id: {padded_feature_id}" in final_body  # fenced block: untouched
    assert f"`{padded_bug_id}`" in final_body  # inline code span: untouched
    assert f"Filed against {bug_filename}" in final_body  # filename reference: untouched
    assert padded_feature_id not in final_body.split("```")[0].split("Filed against")[0]

    # --- filenames are never touched, and the file the reference names still exists ---
    assert task_path.name == task_filename_before
    assert task_path.is_file()
    assert (svc.paths.abspath(bug.path).parent / bug_filename).is_file()

    # --- the rewritten parent/ref still resolve to the right item, and frontmatter/index
    # reconcile cleanly (no drift warnings from the hand-devolved-then-migrated files) ---
    assert (await svc.get(task_fm["parent"])).id == feature.id
    assert (await svc.get(task_fm["refs"][0])).id == bug.id
    issues = await svc.check()
    assert not issues, f"expected a clean check, got: {issues}"

    # --- idempotent: a second pass changes nothing ---
    assert _v0_5_to_v0_7.migrate(svc.paths) == 0
