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


# Same "action" kind as above, plus a non-severity field ("urgency") to prove the generic
# field-code store: bound to its own ordered collection, exactly ADR-323's field mechanism
# reused on the sub-entity axis (no severity-special-casing survives the CLI wiring).
_WORKFLOW_OVERRIDE_WITH_FIELD = """\
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

[collections.level]
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
"""


def _write_overrides(squad_dir: Path, workflow_toml: str = _WORKFLOW_OVERRIDE) -> None:
    override_dir = squad_dir / ".overrides"
    (override_dir).mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(workflow_toml, encoding="utf-8")
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


async def test_custom_kind_declared_field_is_settable_and_round_trips(project, invoke) -> None:
    """A custom kind's non-severity field (``urgency``) is settable via add-<kind>/update,
    stored generically (SubEntity.extra), and round-trips through frontmatter, the summary
    column, and a --json (no-spec) read — the direct analog of the item badge axis."""
    _write_overrides(project.squad_dir, _WORKFLOW_OVERRIDE_WITH_FIELD)

    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    inc_num = _num(_created_id(created.output))

    # add-<kind>: the --urgency flag is derived from the declared field, not hand-written.
    added = await invoke(
        ["incident", inc_num, "add-action", "Restart service", "--urgency", "high"]
    )
    assert added.exit_code == 0, added.output
    assert "AC1" in added.output

    # renders in the derived summary column (Urgency), rendered as its collection's badge.
    listed = await invoke(["incident", inc_num, "actions"])
    assert listed.exit_code == 0, listed.output
    assert "Urgency" in listed.output
    assert "high" in listed.output

    # update: --urgency remaps the stored code.
    updated = await invoke(["incident", inc_num, "action", "1", "update", "--urgency", "low"])
    assert updated.exit_code == 0, updated.output

    listed_after = await invoke(["incident", inc_num, "actions"])
    assert "low" in listed_after.output and "high" not in listed_after.output

    # round-trips in frontmatter: the generic store is SubEntity.extra, persisted on disk.
    inc_path = next((project.squad_dir / "incidents").glob("INC-*-outage.md"))
    on_disk = inc_path.read_text(encoding="utf-8")
    assert "urgency: low" in on_disk

    # --json / no-spec read: the stored badge code is the item's own model dump, no
    # label/emoji resolution needed to read it back.
    shown_json = await invoke(["incident", inc_num, "show", "--json"])
    assert shown_json.exit_code == 0, shown_json.output
    data = json.loads(shown_json.output)
    assert data["subentities"][0]["extra"]["urgency"] == "low"
