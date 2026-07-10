"""A custom sub-entity kind's whole CLI surface — ``add-<kind>``, the ``<plural>`` list verb, and
the nested ``<kind> <n> show/update/body/comment`` subgroup — is built generically from the
resolved ``SubentityKindSpec``, with zero code change (mirrors the ADR's own "incident declares
an action kind" example). A declared non-severity field is settable/round-trips exactly like the
item badge axis (SubEntity.extra, not a severity-only slot).
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

# Same "action" kind, plus a non-severity field ("urgency") bound to its own ordered collection —
# proves the badge/field mechanism is reused on the sub-entity axis, with no severity special-
# casing surviving the wiring.
_WORKFLOW_OVERRIDE_WITH_FIELD = _WORKFLOW_OVERRIDE.replace(
    '[subentity_kinds.action]\nlifecycle = "action"\ncompletion = "Done"\n'
    'plural = "actions"\nlocal_prefix = "AC"\n',
    """[collections.level]
label = "Level"
ordered = true
badges = [
  { code = "high", label = "High", emoji = "\U0001f534" },
  { code = "low", label = "Low", emoji = "\U0001f7e2" },
]

[subentity_kinds.action]
lifecycle = "action"
completion = "Done"
plural = "actions"
local_prefix = "AC"
fields = [
  { code = "urgency", label = "Urgency", collection = "level" },
]
""",
)


def _write_overrides(squad_dir: Path, workflow_toml: str = _WORKFLOW_OVERRIDE) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(workflow_toml, encoding="utf-8")
    template_dir = override_dir / "templates" / "items"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "incident.md.j2").write_text(_INCIDENT_TEMPLATE, encoding="utf-8")
    invalidate_squad_dir(squad_dir)  # evict the pre-existing-template env cache


def _created_id(output: str) -> str:
    m = re.search(r"INC-(\d+)", output)
    assert m is not None, f"could not find an INC-N id in:\n{output}"
    return m.group(0)


def _num(item_id: str) -> str:
    return item_id.rsplit("-", 1)[-1]


async def test_add_list_and_mutation_verbs_all_work_with_no_code_change(project, invoke) -> None:
    _write_overrides(project.squad_dir)

    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    inc_num = _num(_created_id(created.output))

    added = await invoke(["incident", inc_num, "add-action", "Restart service"])
    assert added.exit_code == 0 and "AC1" in added.output

    listed = await invoke(["incident", inc_num, "actions"])
    assert listed.exit_code == 0
    assert "Action" in listed.output
    assert "AC1" in listed.output and "Restart service" in listed.output

    listed_json = await invoke(["incident", inc_num, "actions", "--json"])
    assert json.loads(listed_json.output) == [
        {
            "local_id": "AC1",
            "title": "Restart service",
            "status": "Open",
            "assignee": None,
            "severity": None,
            "story": None,
        }
    ]

    updated = await invoke(["incident", inc_num, "action", "1", "update", "--status", "InProgress"])
    assert updated.exit_code == 0, updated.output

    body_set = await invoke(
        ["incident", inc_num, "action", "1", "body", "-m", "Restarted the service."]
    )
    assert body_set.exit_code == 0, body_set.output

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
    assert shown.exit_code == 0
    assert "InProgress" in shown.output
    assert "Restarted the service." in shown.output
    assert "Health checks green." in shown.output

    full = await invoke(["incident", inc_num, "show", "--full"])
    assert full.exit_code == 0 and "AC1" in full.output


async def test_a_declared_non_severity_field_is_settable_and_round_trips(project, invoke) -> None:
    _write_overrides(project.squad_dir, _WORKFLOW_OVERRIDE_WITH_FIELD)

    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    inc_num = _num(_created_id(created.output))

    added = await invoke(
        ["incident", inc_num, "add-action", "Restart service", "--urgency", "high"]
    )
    assert added.exit_code == 0, added.output

    listed = await invoke(["incident", inc_num, "actions"])
    assert "Urgency" in listed.output and "high" in listed.output

    updated = await invoke(["incident", inc_num, "action", "1", "update", "--urgency", "low"])
    assert updated.exit_code == 0, updated.output
    listed_after = await invoke(["incident", inc_num, "actions"])
    assert "low" in listed_after.output and "high" not in listed_after.output

    on_disk = next((project.squad_dir / "incidents").glob("INC-*-outage.md")).read_text(
        encoding="utf-8"
    )
    assert "urgency: low" in on_disk

    shown_json = await invoke(["incident", inc_num, "show", "--json"])
    data = json.loads(shown_json.output)
    assert data["subentities"][0]["extra"]["urgency"] == "low"

    shown = await invoke(["incident", inc_num, "action", "1", "show"])
    assert "urgency: low" in shown.output
