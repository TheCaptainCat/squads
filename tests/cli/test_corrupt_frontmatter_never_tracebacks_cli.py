"""The load boundary's guarantee as an operator actually experiences it: a clean one-line error and
a documented exit code, never a Rich traceback.

The service-level sweep proves the boundary raises `SquadsError`; this proves the CLI turns that
into a message rather than a stack. The two are not the same claim -- an exception escaping as a
builtin still "raises" at the service layer, and the only surface where the difference is visible
is here. Asserting on the absence of "Traceback" is deliberate: it is the exact string the operator
saw for six of the shapes.
"""

import pytest

from _helpers import create_item
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio

#: One representative per exception the coercion used to throw past the boundary, so a regression in
#: any single arm is caught here too rather than only in the service sweep: `TypeError` (`labels`),
#: `ValueError` (`extra`, `created_at`), `AttributeError` (`id`), plus a `subentities` element.
_SHAPES: list[tuple[str, str, object]] = [
    ("labels_int", "labels", 5),
    ("refs_int", "refs", 5),
    ("extra_str", "extra", "oops"),
    ("subentities_int_element", "subentities", [5]),
    ("created_at_unparseable", "created_at", "not-a-date"),
    ("id_int", "id", 5),
]
_IDS = [name for name, _, _ in _SHAPES]
_ARGS = [(key, value) for _, key, value in _SHAPES]


@pytest.mark.parametrize(("key", "value"), _ARGS, ids=_IDS)
async def test_check_and_repair_report_a_corrupt_field_without_a_traceback(invoke, svc, key, value):
    bad = (await create_item(svc, "task", "a task with a type-invalid field")).item
    path = svc.paths.abspath(bad.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm[key] = value
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    check = await invoke(["check"])
    assert check.exit_code == 3, check.output  # 3 == error-level issues found, the documented code
    assert "Traceback" not in check.output
    assert path.name in check.output

    repair = await invoke(["repair"])
    assert "Traceback" not in repair.output
    assert path.name in repair.output


@pytest.mark.parametrize(("key", "value"), _ARGS, ids=_IDS)
async def test_a_single_item_verb_reports_a_corrupt_field_without_a_traceback(
    invoke, svc, key, value
):
    """The widened blast radius, at the CLI: after the boundary moved, every single-item verb on the
    corrupt item reaches it. Exit 1 (a plain command error), not 3 (a check finding)."""
    bad = (await create_item(svc, "task", "a task with a type-invalid field")).item
    path = svc.paths.abspath(bad.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm[key] = value
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    result = await invoke(["task", str(bad.sequence_id), "status", "InProgress"])

    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    assert "invalid item data" in result.output


async def test_a_malformed_id_is_reported_per_file_rather_than_aborting_the_check(invoke, svc):
    """`sq check` used to exit on the first malformed `id`, having reported nothing else. The
    healthy sibling's own issue appearing in the same run is what proves the scan continued."""
    sibling = (await create_item(svc, "task", "a sibling with its own problem")).item
    sibling_path = svc.paths.abspath(sibling.path)
    sibling_path.write_text(
        sibling_path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", ""),
        encoding="utf-8",
    )
    bad = (await create_item(svc, "task", "a task with a malformed id")).item
    bad_path = svc.paths.abspath(bad.path)
    fm, body = split_frontmatter(bad_path.read_text(encoding="utf-8"))
    fm["id"] = "TASK-abc"
    bad_path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    result = await invoke(["check"])

    assert result.exit_code == 3, result.output
    assert "Traceback" not in result.output
    assert bad_path.name in result.output
    assert sibling_path.name in result.output
