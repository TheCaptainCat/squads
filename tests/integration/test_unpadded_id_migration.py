"""Schema 0.5 -> 0.7 migration: unpad frontmatter id/parent/refs and body-prose id mentions —
while leaving fenced/inline code spans and filename references (which are never renamed) alone.
"""

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _v0_5_to_v0_7
from squads._models._item import DEFAULT_ID_PADDING, format_item_id

pytestmark = pytest.mark.anyio


def _pad(ref: str) -> str:
    """Pad a bare id or an ``ID:kind`` ref entry from its own trailing digits, keeping any
    kind suffix intact — the migration fixture's own devolve-to-pre-migration step, so it has
    to be able to express a spelled ref the same way a pre-0.7 corpus could."""
    rid, _, kind = ref.partition(":")
    prefix, _, digits = rid.rpartition("-")
    padded = format_item_id(prefix, int(digits), DEFAULT_ID_PADDING)
    return f"{padded}:{kind}" if kind else padded


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
    feature = (await create_item(svc, "feature", "Login")).item
    bug = (await create_item(svc, "bug", "Session leak")).item
    task = (await create_item(svc, "task", "Implement auth", parent=feature.id, refs=[bug.id])).item
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
    # `_devolve_to_padded`'s subentity-title overwrite (above) never touched the index, only
    # the file — a bypass this migration's own MANUAL text accounts for as its step 4
    # ("Runs `sq repair` to rebuild the index"). Do that before asserting a clean check, same
    # as a real `sq migrate up` would.
    await svc.repair()
    issues = await svc.check()
    assert not issues

    assert _v0_5_to_v0_7.migrate(svc.paths) == 0  # idempotent


def test_unpad_ref_matches_the_pre_structural_ref_encoding_byte_for_byte():
    """Every row asserted on bytes against what this runner produced before ``make_ref``
    became structural (driven at ``958974c^``, the commit before the ref-kind vocabulary
    landing): a spelled declared-default kind is the only row that ever moved, and it must
    collapse back to bare."""
    unpad = _v0_5_to_v0_7._unpad_ref

    assert unpad("TASK-000007:related") == "TASK-7"  # spelled default -> collapses to bare
    assert unpad("TASK-000007") == "TASK-7"  # already bare
    assert unpad("TASK-000007:blocks") == "TASK-7:blocks"  # non-default stays spelled
    assert unpad("TASK-000007:") == "TASK-7"  # empty kind suffix -> bare
    assert unpad("TASK-000007:scopes") == "TASK-7:scopes"  # non-default stays spelled
    assert unpad("not-an-id") == "not-an-id"  # malformed -- left untouched


def test_v0_5_to_v0_7_never_imports_the_live_ref_encoding_primitives():
    """Structural proof alongside the ``tests/meta`` import-hygiene guard: the module holds no
    reference to the live ``squads._models._item`` ref/id-formatting primitives at all -- its
    own frozen copies are distinct function objects, not re-exports."""
    assert not hasattr(_v0_5_to_v0_7, "make_ref")
    assert not hasattr(_v0_5_to_v0_7, "split_ref")
    assert not hasattr(_v0_5_to_v0_7, "format_item_id")
    assert not hasattr(_v0_5_to_v0_7, "DISPLAY_ID_PADDING")


async def test_migration_collapses_a_spelled_default_kind_and_keeps_a_spelled_non_default(svc):
    """The end-to-end complement to the byte assertion above: a repad fixture whose ``refs``
    carry a spelled default-kind ref and a spelled non-default ref, migrated through the actual
    file the runner writes rather than the helper in isolation."""
    task = (await create_item(svc, "task", "t")).item
    default_target = (await create_item(svc, "task", "d")).item
    other_target = (await create_item(svc, "task", "o")).item

    await _devolve_to_padded(
        svc,
        task.id,
        parent=None,
        refs=[f"{default_target.id}:related", f"{other_target.id}:blocks", other_target.id],
    )

    changed = _v0_5_to_v0_7.migrate(svc.paths)
    assert changed == 1

    task_fm = read_frontmatter(svc.paths.abspath((await svc.get(task.id)).path))
    assert task_fm["refs"] == [default_target.id, f"{other_target.id}:blocks", other_target.id]
