"""End-to-end proof that a custom sub-entity kind's whole CLI surface (add-<kind>, the
<plural> list verb, and the nested <kind> <n> show/update/body/comment subgroup) is built
generically from the resolved SubentityKindSpec — no code change, mirroring the ADR's own
"incident declares an action kind" example.
"""

import json
import re
from pathlib import Path

import pytest

from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_WORKFLOW_OVERRIDE = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done"]
Done = []

[lifecycles.action]
initial = "Open"
[lifecycles.action.transitions]
Open = ["InProgress", "Done"]
InProgress = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
subentity_kind = "action"

[subentity_kinds.action]
lifecycle = "action"
completion = "Done"
plural = "actions"
local_prefix = "AC"
"""

# Mirrors feature.md.j2's shape (summary + container) with "actions" in place of "stories" —
# a project declaring a custom sub-entity kind supplies its own item template the same way it
# already supplies its own workflow vocabulary.
_INCIDENT_TEMPLATE = """\
<!-- sq:body -->
## Summary

_TODO: summarise this incident._
<!-- sq:body:end -->

## Actions

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:actions -->
<!-- sq:actions:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
"""


def _write_overrides(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    (override_dir).mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_WORKFLOW_OVERRIDE, encoding="utf-8")
    template_dir = override_dir / "templates" / "items"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "incident.md.j2").write_text(_INCIDENT_TEMPLATE, encoding="utf-8")
    # The rendering env is cached per squad_dir at first use (e.g. by squad init, before this
    # override existed on disk) — evict it so the new template is picked up.
    invalidate_squad_dir(squad_dir)


def _created_id(output: str) -> str:
    m = re.search(r"INC-(\d+)", output)
    assert m is not None, f"could not find an INC-N id in:\n{output}"
    return m.group(0)


def _num(item_id: str) -> str:
    return item_id.rsplit("-", 1)[-1]


async def test_custom_kind_add_list_and_mutation_verbs_work_with_no_code_change(
    project, invoke
) -> None:
    _write_overrides(project.squad_dir)

    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    inc_num = _num(_created_id(created.output))

    # add-<kind>: dynamically built from the resolved SubentityKindSpec, no --action-* flags
    # declared anywhere in source (the kind has no custom fields).
    added = await invoke(["incident", inc_num, "add-action", "Restart service"])
    assert added.exit_code == 0, added.output
    assert "AC1" in added.output

    # <plural> list verb: columns derived from discussion.summary_columns (kind.title() + the
    # base Status/Assignee/Title set — no fields declared, so no extra badge column).
    listed = await invoke(["incident", inc_num, "actions"])
    assert listed.exit_code == 0, listed.output
    assert "Action" in listed.output
    assert "AC1" in listed.output and "Restart service" in listed.output

    listed_json = await invoke(["incident", inc_num, "actions", "--json"])
    assert listed_json.exit_code == 0, listed_json.output
    rows = json.loads(listed_json.output)
    assert rows == [
        {
            "local_id": "AC1",
            "title": "Restart service",
            "status": "Open",
            "assignee": None,
            "severity": None,
            "story": None,
        }
    ]

    # <kind> <n> update: status transition resolved against the kind's own "action" machine.
    updated = await invoke(["incident", inc_num, "action", "1", "update", "--status", "InProgress"])
    assert updated.exit_code == 0, updated.output

    # <kind> <n> body
    body_set = await invoke(
        ["incident", inc_num, "action", "1", "body", "-m", "Restarted the service."]
    )
    assert body_set.exit_code == 0, body_set.output

    # <kind> <n> comment: exercises the generic (kind, local_id) discussion-tag resolution.
    commented = await invoke(
        [
            "incident",
            inc_num,
            "action",
            "1",
            "comment",
            "-m",
            "Health checks green.",
            "--as",
            "manager",
        ]
    )
    assert commented.exit_code == 0, commented.output

    shown = await invoke(["incident", inc_num, "action", "1", "show"])
    assert shown.exit_code == 0, shown.output
    assert "InProgress" in shown.output
    assert "Restarted the service." in shown.output
    assert "Health checks green." in shown.output

    # sq incident <n> show --full renders one pane per sub-entity via the generic get_block path.
    full = await invoke(["incident", inc_num, "show", "--full"])
    assert full.exit_code == 0, full.output
    assert "AC1" in full.output
