"""`sq import`: applying a JSONL file of events in one transaction, checking it first, and
refusing it whole."""

import json
from pathlib import Path
from typing import Any

import pytest

from tests._squadwide import listed

pytestmark = pytest.mark.anyio

CREATE = {"op": "create", "type": "task", "title": "Imported", "handle": "t", "as": "manager"}
COMMENT = {"op": "comment", "target": "t", "message": "hello"}
PLAN = "  create: 1\n  comment: 1\nhandles:\n  t -> TASK-2\n"
ONLY_ROLE = [("ROLE-1", "Catherine Manager")]
IMPORTED = [*ONLY_ROLE, ("TASK-2", "Imported")]


def _events(*events: dict[str, Any]) -> str:
    """Write *events* as a JSONL file in the working directory; return its name."""
    Path("events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    return "events.jsonl"


@pytest.mark.covers("import", "FILE")
async def test_file_applies_its_events_and_reports_the_ids_it_gave(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT)])
    assert (result.exit_code, result.output) == (0, PLAN + "imported 2 event(s)\n")
    assert await listed(invoke) == IMPORTED
    shown = await invoke(["task", "2", "show", "--json"])
    task = json.loads(shown.output)
    assert (task["author"], [c["body"] for c in task["discussion"]]) == ("manager", ["- hello"])


@pytest.mark.covers("import", "FILE")
async def test_file_dash_reads_the_events_from_standard_input(project, invoke) -> None:
    result = await invoke(["import", "-"], input=json.dumps(CREATE) + "\n")
    assert (result.exit_code, result.output) == (
        0,
        "  create: 1\nhandles:\n  t -> TASK-2\nimported 1 event(s)\n",
    )
    assert await listed(invoke) == IMPORTED


@pytest.mark.covers("import", "FILE")
async def test_file_refuses_a_path_that_cannot_be_read(project, invoke) -> None:
    result = await invoke(["import", "missing.jsonl"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot read import file 'missing.jsonl': No such file or directory\n",
    )


@pytest.mark.covers("import", "FILE")
async def test_file_is_required(project, invoke) -> None:
    result = await invoke(["import"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq import [OPTIONS] FILE\nTry 'sq import --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'FILE'.                                                     │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("import", "--dry-run")
async def test_dry_run_prints_the_plan_and_writes_nothing(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT), "--dry-run"])
    assert (result.exit_code, result.output) == (0, PLAN + "dry run — nothing written\n")
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "--as")
async def test_as_attributes_an_event_that_names_no_actor(project, invoke) -> None:
    anonymous = {k: v for k, v in CREATE.items() if k != "as"}
    result = await invoke(["import", _events(anonymous), "--as", "manager"])
    assert result.exit_code == 0, result.output
    shown = await invoke(["task", "2", "show", "--json"])
    assert json.loads(shown.output)["author"] == "manager"


@pytest.mark.covers("import", "FILE")
async def test_an_event_with_no_actor_is_refused_without_as(project, invoke) -> None:
    anonymous = {k: v for k, v in CREATE.items() if k != "as"}
    result = await invoke(["import", _events(anonymous)])
    assert (result.exit_code, result.output) == (
        1,
        "line 1: no actor: missing 'as'\n1 issue(s) found — nothing written.\n",
    )
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "--as")
async def test_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    anonymous = {k: v for k, v in CREATE.items() if k != "as"}
    result = await invoke(["import", _events(anonymous), "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "line 1: author 'nobody' is not a registered role or operator — register it first\n"
        "1 issue(s) found — nothing written.\n",
    )


@pytest.mark.covers("import", "--json")
async def test_json_prints_the_plan_and_the_outcome_of_an_applied_file(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "op_counts": {"create": 1, "comment": 1},
        "handle_to_id": {"t": "TASK-2"},
        "handle_to_sub": {},
        "issues": [],
        "ok": True,
        "applied": True,
        "dry_run": False,
        "created_ids": ["TASK-2"],
        "warnings": [],
    }


@pytest.mark.covers("import", "--dry-run", "--json")
async def test_json_with_dry_run_reports_the_plan_as_not_applied(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT), "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert (payload["applied"], payload["dry_run"], payload["created_ids"]) == (False, True, [])
    assert payload["handle_to_id"] == {"t": "TASK-2"}
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "--json")
async def test_json_lists_every_refusal_by_line_and_exits_1(project, invoke) -> None:
    result = await invoke(
        [
            "import",
            _events(CREATE, {"op": "status", "target": "TASK-99", "status": "Ready"}),
            "--json",
        ]
    )
    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "op_counts": {"create": 1, "status": 1},
        "handle_to_id": {"t": "TASK-2"},
        "handle_to_sub": {},
        "issues": [{"line": 2, "message": "no item 'TASK-99' in the index"}],
        "ok": False,
        "applied": False,
        "dry_run": False,
        "created_ids": [],
        "warnings": [],
    }


@pytest.mark.covers("import", "FILE")
async def test_a_refused_line_leaves_the_valid_events_before_it_unapplied(project, invoke) -> None:
    events = _events(
        CREATE, {"op": "nope"}, {"op": "status", "target": "TASK-99", "status": "Ready"}
    )
    result = await invoke(["import", events])
    assert result.exit_code == 1
    assert result.output.splitlines() == [
        "line 2: unknown op 'nope'; valid ops: create, status, body, comment, ref, add-sub, "
        "add-story, add-subtask, add-finding, sub-status, sub-body, assign, update",
        "line 3: no item 'TASK-99' in the index",
        "2 issue(s) found — nothing written.",
    ]
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "FILE")
async def test_an_event_refused_while_applying_undoes_the_events_before_it(project, invoke) -> None:
    events = _events(
        CREATE,
        {"op": "body", "target": "t", "body": "one"},
        {"op": "body", "target": "t", "body": "two"},
    )
    result = await invoke(["import", events])
    assert (result.exit_code, result.output) == (
        1,
        "error: TASK-2 already has a body (1 line); setting one would discard it:\n\n    one\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    assert await listed(invoke) == ONLY_ROLE


def _host(
    op: str, handle: str, kind: str, title: str, sub_handle: str | None = None
) -> list[dict[str, Any]]:
    host = {"op": "create", "type": op, "title": title, "handle": handle, "as": "manager"}
    return [
        host,
        {"op": "add-sub", "target": handle, "kind": kind, "title": "Part"}
        | ({"handle": sub_handle} if sub_handle else {}),
    ]


HOSTS = [
    *_host("feature", "f", "story", "Feature"),
    *_host("task", "t", "subtask", "Task"),
    *_host("review", "r", "finding", "Review"),
]
HOST_IDS = {
    "story": ("feature", "2", "f"),
    "subtask": ("task", "3", "t"),
    "finding": ("review", "4", "r"),
}
LOCAL = {"story": "US1", "subtask": "ST1", "finding": "F1"}
TOO_MANY = "a comment event names at most one of story / subtask / finding / sub"


def _comment(kind: str, **selectors: Any) -> dict[str, Any]:
    return {"op": "comment", "target": HOST_IDS[kind][2], "message": "note", **selectors}


async def _discussion(invoke, kind: str) -> list[str]:
    type_, number, _handle = HOST_IDS[kind]
    shown = await invoke([type_, number, kind, LOCAL[kind], "show", "--json"])
    assert shown.exit_code == 0, shown.output
    return [c["body"] for c in json.loads(shown.output)["discussion"]]


@pytest.mark.covers("import", "FILE")
@pytest.mark.parametrize("kind", ["story", "subtask", "finding"])
@pytest.mark.parametrize("spelled", ["field", "sub"])
async def test_a_comment_event_selector_lands_in_that_sub_entity(
    project, invoke, kind, spelled
) -> None:
    selector = {kind: LOCAL[kind]} if spelled == "field" else {"sub": [kind, LOCAL[kind]]}
    result = await invoke(["import", _events(*HOSTS, _comment(kind, **selector))])
    assert result.exit_code == 0, result.output
    assert await _discussion(invoke, kind) == ["- note"]
    for other in set(HOST_IDS) - {kind}:
        assert await _discussion(invoke, other) == []


@pytest.mark.covers("import", "FILE")
@pytest.mark.parametrize("kind", ["story", "subtask", "finding"])
@pytest.mark.parametrize("spelled", ["field", "sub"])
async def test_a_comment_event_selector_can_name_an_add_sub_handle(
    project, invoke, kind, spelled
) -> None:
    hosts = [
        *_host("feature", "f", "story", "Feature", sub_handle="hs"),
        *_host("task", "t", "subtask", "Task", sub_handle="hst"),
        *_host("review", "r", "finding", "Review", sub_handle="hf"),
    ]
    handle = {"story": "hs", "subtask": "hst", "finding": "hf"}[kind]
    selector = {kind: handle} if spelled == "field" else {"sub": [kind, handle]}
    result = await invoke(["import", _events(*hosts, _comment(kind, **selector))])
    assert result.exit_code == 0, result.output
    assert await _discussion(invoke, kind) == ["- note"]
    for other in set(HOST_IDS) - {kind}:
        assert await _discussion(invoke, other) == []


@pytest.mark.covers("import", "FILE")
async def test_a_comment_event_without_a_selector_lands_on_the_item(project, invoke) -> None:
    result = await invoke(["import", _events(*HOSTS, _comment("subtask"))])
    assert result.exit_code == 0, result.output
    shown = await invoke(["task", "3", "show", "--json"])
    assert [c["body"] for c in json.loads(shown.output)["discussion"]] == ["- note"]
    assert await _discussion(invoke, "subtask") == []


@pytest.mark.covers("import", "FILE")
@pytest.mark.parametrize(
    "selectors",
    [
        {"story": "US1", "subtask": "ST1"},
        {"subtask": "ST1", "sub": ["subtask", "ST1"]},
        {"story": "US1", "subtask": "ST1", "finding": "F1"},
    ],
)
async def test_a_comment_event_naming_two_selectors_is_refused_and_writes_nothing(
    project, invoke, selectors
) -> None:
    result = await invoke(["import", _events(*HOSTS, _comment("subtask", **selectors))])
    assert (result.exit_code, result.output) == (
        1,
        f"line 7: {TOO_MANY}\n1 issue(s) found — nothing written.\n",
    )
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "FILE")
@pytest.mark.parametrize(
    ("kind", "selector"),
    [("subtask", {"subtask": "ST9"}), ("story", {"sub": ["story", "US9"]})],
)
async def test_a_comment_event_naming_an_unknown_sub_entity_is_refused(
    project, invoke, kind, selector
) -> None:
    result = await invoke(["import", _events(*HOSTS, _comment(kind, **selector))])
    missing = "ST9 in TASK-3" if kind == "subtask" else "US9 in FEAT-2"
    assert (result.exit_code, result.output) == (
        1,
        f"line 7: no {kind} {missing}\n1 issue(s) found — nothing written.\n",
    )
    assert await listed(invoke) == ONLY_ROLE


# --- the override squad: kinds, fields and mapping keys follow the declared vocabulary ----------

AS = {"as": "manager"}


async def _import_ok(invoke, *events: dict[str, Any]) -> str:
    result = await invoke(["import", _events(*events)])
    assert result.exit_code == 0, result.output
    return result.output


async def _shown(invoke, *address: str) -> dict[str, Any]:
    result = await invoke([*address, "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.covers("import", "FILE")
async def test_add_kind_takes_each_field_and_the_target_kind_as_keys_and_a_comment_names_the_kind(
    override_project, invoke
) -> None:
    output = await _import_ok(
        invoke,
        {"op": "add-outcome", "target": "INI-8", "title": "A third outcome", "handle": "o3", **AS},
        {
            "op": "add-action",
            "target": "JOB-9",
            "title": "Ship it",
            "impact": "small",
            "outcome": "OC1",
            "handle": "a3",
        },
        {"op": "comment", "target": "INI-8", "outcome": "OC3", "message": "agreed"},
        {"op": "comment", "target": "JOB-9", "action": "a3", "message": "shipped"},
    )
    assert output == (
        "  add-outcome: 1\n  add-action: 1\n  comment: 2\n"
        "handles:\n  o3 -> INI-8 OC3\n  a3 -> JOB-9 AC3\n"
        "warning: INI-8: OC3 body is unwritten (still the placeholder stub)\n"
        "warning: JOB-9: AC3 body is unwritten (still the placeholder stub)\n"
        "imported 4 event(s)\n"
    )
    action = await _shown(invoke, "job", "9", "action", "3")
    assert (action["badges"], action["story"]) == ({"impact": "small"}, "OC1")
    outcome = await _shown(invoke, "initiative", "8", "outcome", "3")
    assert [c["body"] for c in outcome["discussion"]] == ["- agreed"]


@pytest.mark.covers("import", "FILE")
async def test_an_op_or_a_selector_for_a_kind_the_squad_does_not_declare_is_unknown(
    override_project, invoke
) -> None:
    events = _events(
        {"op": "add-story", "target": "INI-8", "title": "No such kind", **AS},
        {"op": "comment", "target": "INI-8", "story": "US1", "message": "x", **AS},
    )
    result = await invoke(["import", events])
    assert result.exit_code == 1
    assert result.output.splitlines() == [
        "line 1: unknown op 'add-story'; valid ops: create, status, body, comment, ref, "
        "add-sub, add-outcome, add-action, sub-status, sub-body, assign, update",
        "line 2: comment.story: not a key of comment; the sub-entity selectors are outcome, "
        "action, sub",
        "2 issue(s) found — nothing written.",
    ]


@pytest.mark.covers("import", "FILE")
async def test_add_sub_takes_the_mapping_as_maps_to_and_the_fields_in_fields(
    override_project, invoke
) -> None:
    await _import_ok(
        invoke,
        {
            "op": "add-sub",
            "target": "JOB-9",
            "kind": "action",
            "title": "Verify",
            "maps_to": "OC2",
            "fields": {"impact": "large"},
            **AS,
        },
    )
    action = await _shown(invoke, "job", "9", "action", "3")
    assert (action["badges"], action["story"]) == ({"impact": "large"}, "OC2")
    named = {"op": "add-sub", "target": "JOB-9", "kind": "action", "title": "T", "outcome": "OC1"}
    refused = await invoke(["import", _events(named | AS)])
    assert (refused.exit_code, refused.output) == (
        1,
        "line 1: add-sub.outcome: not a key of add-sub; use 'maps_to' for the mapping\n"
        "1 issue(s) found — nothing written.\n",
    )


@pytest.mark.covers("import", "FILE")
async def test_create_and_update_take_badge_fields_by_code_in_fields_and_unset_fields(
    override_project, invoke
) -> None:
    sized = {"op": "create", "type": "job", "parent": "INI-8", "fields": {"work_size": "s"}}
    await _import_ok(
        invoke,
        {**sized, "title": "Sized", "handle": "j", **AS},
        {"op": "update", "target": "j", "fields": {"work_size": "l"}},
        {**sized, "title": "Unsized", "handle": "u"},
        {"op": "update", "target": "u", "unset_fields": ["work_size"]},
    )
    assert (await _shown(invoke, "job", "11"))["badges"] == {"work_size": "l"}
    assert (await _shown(invoke, "job", "12"))["badges"] == {}
    keyed = {"op": "create", "type": "initiative", "title": "Keyed", "urgency": "now"}
    refused = await invoke(["import", _events(keyed | AS)])
    assert (refused.exit_code, refused.output) == (
        1,
        "line 1: create.urgency: Extra inputs are not permitted\n"
        "1 issue(s) found — nothing written.\n",
    )


@pytest.mark.covers("import", "FILE")
async def test_a_stray_key_on_add_kind_is_reported_under_the_op_the_file_wrote(
    override_project, invoke
) -> None:
    stray = {"op": "add-action", "target": "JOB-9", "title": "T", "severity": "high"}
    refused = await invoke(["import", _events(stray | AS)])
    assert (refused.exit_code, refused.output) == (
        1,
        "line 1: add-action.severity: Extra inputs are not permitted\n"
        "1 issue(s) found — nothing written.\n",
    )


@pytest.mark.covers("import", "FILE")
async def test_the_old_story_key_on_add_sub_points_to_maps_to_and_an_empty_field_is_unset(
    project, invoke
) -> None:
    host = {"op": "create", "type": "review", "title": "R", "handle": "r", **AS}
    findings = [
        {"op": "add-finding", "target": "r", "title": f"F {n}", "severity": value}
        for n, value in enumerate((None, ""))
    ]
    await _import_ok(invoke, host, *findings)
    assert [(await _shown(invoke, "review", "2", "finding", str(n)))["badges"] for n in (1, 2)] == [
        {},
        {},
    ]
    old = {"op": "add-sub", "target": "r", "kind": "subtask", "title": "T", "story": "US1"}
    refused = await invoke(["import", _events(old | AS)])
    assert (refused.exit_code, refused.output) == (
        1,
        "line 1: add-sub.story: not a key of add-sub; use 'maps_to' for the mapping\n"
        "1 issue(s) found — nothing written.\n",
    )
