"""An import's findings come back in the order `sq check` prints them, whatever order the type's
validators run in, in both the warnings and the structured findings."""

from pathlib import Path

import pytest

from squads import __version__
from squads._services import _service as service
from squads._services._results import check_issue_sort_key

pytestmark = pytest.mark.anyio

_LONG = "q" * 121

_EVENTS = (
    '{"op":"create","type":"feature","title":"Imp F","handle":"f1","as":"manager",'
    '"body":"## Status\\n\\nx"}\n'
    f'{{"op":"add-story","target":"f1","title":"{_LONG}","handle":"s1"}}\n'
    '{"op":"create","type":"task","title":"Imp T","handle":"t1","parent":"f1","as":"manager",'
    '"body":"STATUS: x"}\n'
    f'{{"op":"add-subtask","target":"t1","title":"{_LONG}"}}\n'
)

#: The validators entries the feature and task types select, in the orders the list can take.
_SELECTIONS = [
    pytest.param('["no_status_banner", "subentity_title_max:120"]', id="banner-then-title"),
    pytest.param('["subentity_title_max:120", "no_status_banner"]', id="title-then-banner"),
    pytest.param('["subentity_title_max:120"]', id="title-only"),
]


def _open(squad_dir: Path, selection: str) -> service.Service:
    (squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    text = f"# squads:override-base:{__version__}\n" + "".join(
        f"[items.{t}]\nvalidators = {selection}\n\n" for t in ("feature", "task")
    )
    (squad_dir / ".overrides" / "workflow.toml").write_text(text, encoding="utf-8")
    return service.open_service()


@pytest.mark.parametrize("selection", _SELECTIONS)
async def test_import_findings_are_in_check_order_whatever_the_selection(project, selection):
    svc = _open(project.squad_dir, selection)

    result = await svc.import_events(_EVENTS, default_as="manager")

    assert result.applied is not None
    findings = result.applied.findings
    assert findings
    assert findings == sorted(findings, key=check_issue_sort_key)
    lines = [f"{f.item}: {f.message}" for f in findings if f.level != "error"]
    assert result.applied.warnings[-len(lines) :] == lines
