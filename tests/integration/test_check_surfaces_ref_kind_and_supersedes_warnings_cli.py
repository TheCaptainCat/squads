"""`sq check`'s unknown-ref-kind and superseded-without-edge warnings, driven end to end
through the real CLI: create items, corrupt an edge's kind on disk, repair the index, then
confirm the warnings surface in `sq check`'s own text without flipping its exit code. The
rules themselves are proven once at tests/service/test_check_ref_kind_and_supersedes_warnings.py.
"""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_check_cli_prints_both_warnings_and_exits_0(project, invoke):
    from squads._services._service import Service

    svc = Service(project)
    a = (await svc.create("task", "a")).item
    await svc.create("task", "b")
    old_adr = (await svc.create("decision", "old decision")).item

    # Inject an out-of-vocabulary kind directly into frontmatter.
    path = svc.paths.abspath(a.path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["refs"] = ["TASK-000003:junktype"]
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")

    # Force the decision to Superseded with no incoming supersedes edge.
    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)

    await invoke(["repair"])  # sync the index with the rewritten frontmatter

    result = await invoke(["check"])
    assert result.exit_code == 0, result.output  # warnings only — never exit 3
    assert "junktype" in result.output
    assert old_adr.id in result.output
    assert "supersedes" in result.output
