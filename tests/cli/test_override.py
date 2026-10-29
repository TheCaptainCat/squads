"""`sq override …`: scaffolding an override, listing them with their drift state, diffing an
override against the bundled default and re-stamping it after a merge."""

import json
from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from tests.cli._roster import read_json

pytestmark = pytest.mark.anyio

OLD = "0.16.0"
OLD_TEMPLATE = "0.13.1"
TASK = "items/task.md.j2"
FEATURE = "items/feature.md.j2"
STAMP = f"<!-- squads:override-base:{__version__} -->"
TOML_STAMP = f"# squads:override-base:{__version__}"
NOT_UTF8 = "error: Template override {path} is not valid UTF-8; save it as UTF-8 and re-run.\n"


def _path(project, relative: str) -> Path:
    return project.squad_dir / ".overrides" / relative


def _restamp(path: Path, version: str) -> None:
    """Stamp the override at *path* with *version*, as a squad that has not been upgraded would."""
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            f"override-base:{__version__}", f"override-base:{version}"
        ),
        encoding="utf-8",
    )


def _break_utf8(path: Path) -> None:
    """Leave bytes in *path* that no UTF-8 decoder reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe not text")


def _changes(delta: str) -> list[str]:
    """The added and removed lines of a unified diff, without its file headers."""
    return [
        line
        for line in delta.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


async def _scaffold(invoke, *args: str) -> None:
    result = await invoke(["override", "scaffold", *args])
    assert result.exit_code == 0, result.output


async def _drift(invoke, project, *scaffold: str, path: str, version: str = OLD) -> None:
    """Scaffold an override and stamp it with an older *version*, so it lists as drifted."""
    await _scaffold(invoke, *scaffold)
    _restamp(_path(project, path), version)


async def _bystander(invoke, project, *, workflow: bool = False) -> None:
    """A second drifted override, which a command aimed at another override leaves alone."""
    if workflow:
        await _drift(invoke, project, "--workflow", path="workflow.toml")
    else:
        await _drift(invoke, project, TASK, path=f"templates/{TASK}", version=OLD_TEMPLATE)


async def _entries(invoke) -> list[dict[str, Any]]:
    return await read_json(invoke, ["override", "list", "--json"])


async def _diff(invoke, *args: str) -> list[dict[str, Any]]:
    return await read_json(invoke, ["override", "diff", *args, "--json"])


def _entry(name: str, kind: str, base: str | None, state: str) -> dict[str, Any]:
    return {"name": name, "kind": kind, "base_version": base, "state": state}


# ---------------------------------------------------------------------------------- scaffold


@pytest.mark.covers("override scaffold", "NAME")
async def test_scaffold_copies_the_named_template_under_the_current_stamp(project, invoke) -> None:
    result = await invoke(["override", "scaffold", TASK])
    dest = _path(project, f"templates/{TASK}")
    assert result.exit_code == 0, result.output
    assert result.output == (
        f"scaffolded template override: {dest}\n"
        f"Edit {dest}, then verify with sq override diff {TASK}.\n"
    )
    assert await _entries(invoke) == [_entry(TASK, "template", __version__, "current")]
    (diffed,) = await _diff(invoke, TASK)
    assert _changes(diffed["delta_mine"]) == [f"+{STAMP}"]


@pytest.mark.covers("override scaffold", "NAME")
async def test_scaffold_takes_the_documents_by_their_names(project, invoke) -> None:
    for name in ("workflow", "playbook", "roles"):
        await _scaffold(invoke, name)
    assert await _entries(invoke) == [
        _entry("workflow", "workflow", __version__, "current"),
        _entry("playbook", "playbook", __version__, "current"),
        _entry("roles", "roles", __version__, "current"),
    ]


@pytest.mark.covers("override scaffold", "--role")
async def test_scaffold_role_copies_the_bundled_role_fields_commented_out(project, invoke) -> None:
    result = await invoke(["override", "scaffold", "--role", "architect"])
    dest = _path(project, "roles/architect.toml")
    assert result.exit_code == 0, result.output
    assert result.output == (
        f"scaffolded role override: {dest}\n"
        f"Edit {dest} to uncomment the fields to override, then verify with "
        "sq override diff --role architect.\n"
    )
    assert await _entries(invoke) == [
        _entry("architect", "role", __version__, "current"),
    ]
    (diffed,) = await _diff(invoke, "--role", "architect")
    added = [line for line in _changes(diffed["delta_mine"]) if line.startswith("+")]
    assert added[:4] == [
        f"+{TOML_STAMP}",
        "+# Role override for 'architect'. Uncomment a field to override it.",
        '+# full_name = "Robert Architect"',
        '+# title = "architect"',
    ]
    assert '+# model = "opus"' in added


@pytest.mark.covers("override scaffold", "--role")
async def test_scaffold_role_for_a_role_added_by_hand_copies_its_own_fields(
    project, invoke
) -> None:
    added = await invoke(
        [
            "role",
            "add",
            "scout",
            "--name",
            "Sam Scout",
            "--job-title",
            "Scout",
            "--desc",
            "Scouts ahead",
            "--mission",
            "Find things",
        ]
    )
    assert added.exit_code == 0, added.output
    result = await invoke(["override", "scaffold", "--role", "scout"])
    dest = _path(project, "roles/scout.toml")
    assert result.exit_code == 0, result.output
    assert result.output == (
        f"scaffolded role override: {dest}\n"
        f"Edit {dest} to uncomment the fields to override, then verify with "
        "sq override diff --role scout.\n"
    )
    (diffed,) = await _diff(invoke, "--role", "scout")
    added = [line for line in _changes(diffed["delta_mine"]) if line.startswith("+")]
    assert added[:4] == [
        f"+{TOML_STAMP}",
        "+# Role override for 'scout'. Uncomment a field to override it.",
        '+# full_name = "Sam Scout"',
        '+# title = "Scout"',
    ]


@pytest.mark.covers("override scaffold", "--workflow")
async def test_scaffold_workflow_starts_the_workflow_override(project, invoke) -> None:
    result = await invoke(["override", "scaffold", "--workflow"])
    dest = _path(project, "workflow.toml")
    assert result.exit_code == 0, result.output
    assert result.output == (
        f"scaffolded workflow override: {dest}\n"
        f"Edit {dest} to add custom types, statuses, and lifecycles,\n"
        "then validate with sq workflow lint and inspect with sq override diff workflow.\n"
    )
    assert await _entries(invoke) == [
        _entry("workflow", "workflow", __version__, "current"),
    ]
    (diffed,) = await _diff(invoke, "--workflow")
    added = [line for line in _changes(diffed["delta_mine"]) if line.startswith("+")]
    assert added[:2] == [
        f"+{TOML_STAMP}",
        "+# Workflow spec override — shadow or extend the squads built-in vocabulary.",
    ]


@pytest.mark.covers("override scaffold", "--playbook")
async def test_scaffold_playbook_starts_the_playbook_override(project, invoke) -> None:
    result = await invoke(["override", "scaffold", "--playbook"])
    dest = _path(project, "playbook.toml")
    assert result.exit_code == 0, result.output
    assert result.output == (
        f"scaffolded playbook override: {dest}\n"
        f"Edit {dest} to add a role's guidance to a type (the '$(*self)' append idiom), then "
        "inspect with sq override diff playbook.\n"
    )
    assert await _entries(invoke) == [
        _entry("playbook", "playbook", __version__, "current"),
    ]
    (diffed,) = await _diff(invoke, "--playbook")
    added = [line for line in _changes(diffed["delta_mine"]) if line.startswith("+")]
    assert added[:2] == [
        f"+{TOML_STAMP}",
        "+# Playbook spec override — add role guidance to a type's entry, or shadow a bundled one.",
    ]


@pytest.mark.covers("override scaffold", "--roles-catalog")
async def test_scaffold_roles_catalog_starts_the_role_catalog_override(project, invoke) -> None:
    result = await invoke(["override", "scaffold", "--roles-catalog"])
    dest = _path(project, "roles.toml")
    assert result.exit_code == 0, result.output
    assert result.output == (
        f"scaffolded role catalog override: {dest}\n"
        f"Edit {dest} to override [[roles]], [bundles], or [templates.<name>], then inspect "
        "with sq override diff roles.\n"
    )
    assert await _entries(invoke) == [
        _entry("roles", "roles", __version__, "current"),
    ]
    (diffed,) = await _diff(invoke, "--roles-catalog")
    added = [line for line in _changes(diffed["delta_mine"]) if line.startswith("+")]
    assert added[:2] == [
        f"+{TOML_STAMP}",
        "+# Role catalog override — bundles, role templates, and (optionally) roles, all in one",
    ]


@pytest.mark.covers("override scaffold", "--force")
async def test_scaffold_force_replaces_an_override_that_exists(project, invoke) -> None:
    await _scaffold(invoke, TASK)
    with _path(project, f"templates/{TASK}").open("a", encoding="utf-8") as handle:
        handle.write("my own line\n")
    kept = await invoke(["override", "scaffold", TASK])
    assert (kept.exit_code, kept.output) == (
        1,
        f"error: .overrides/templates/{TASK} already exists; use --force to overwrite\n",
    )
    (diffed,) = await _diff(invoke, TASK)
    assert _changes(diffed["delta_mine"]) == [f"+{STAMP}", "+my own line"]

    result = await invoke(["override", "scaffold", TASK, "--force"])
    assert result.exit_code == 0, result.output
    (diffed,) = await _diff(invoke, TASK)
    assert _changes(diffed["delta_mine"]) == [f"+{STAMP}"]


@pytest.mark.covers("override scaffold", "--new")
async def test_scaffold_refuses_the_retired_new_option_and_names_the_replacement(
    project, invoke
) -> None:
    """The option exists only to be refused, so the refusal is the case."""
    result = await invoke(["override", "scaffold", "--new", "ghost"])
    assert (result.exit_code, result.output) == (
        1,
        "error: `sq override scaffold --new` is retired: create the role with "
        "`sq role add ghost --name … --job-title … --desc … --mission …`\n",
    )
    assert await _entries(invoke) == []


async def test_scaffold_refuses_a_template_the_bundle_does_not_have(project, invoke) -> None:
    result = await invoke(["override", "scaffold", "nope.md.j2"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no bundled template 'nope.md.j2' — use a path like 'items/task.md.j2' or "
        "'agents/role.md.j2'\n",
    )
    assert await _entries(invoke) == []


async def test_scaffold_role_refuses_a_role_that_is_neither_bundled_nor_added(
    project, invoke
) -> None:
    result = await invoke(["override", "scaffold", "--role", "ghost"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role 'ghost' to override: create it with `sq role add ghost --name … "
        "--job-title … --desc … --mission …` or `sq role activate ghost`\n",
    )
    assert await _entries(invoke) == []


async def test_scaffold_refuses_a_command_line_that_names_nothing_to_scaffold(
    project, invoke
) -> None:
    result = await invoke(["override", "scaffold"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq override scaffold [OPTIONS] [NAME]\n"
        "Try 'sq override scaffold --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Invalid value: provide a template name (e.g. 'items/<type>.md.j2'),          │\n"
        "│ 'workflow', 'playbook', 'roles', or --role <slug> / --workflow / --playbook  │\n"
        "│ / --roles-catalog to scaffold a role, workflow, playbook, or role-catalog    │\n"
        "│ override                                                                     │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


# ------------------------------------------------------------------------------------- list


@pytest.mark.covers("override list", "--json")
async def test_list_json_gives_each_override_its_kind_base_version_and_state(
    project, invoke
) -> None:
    await _scaffold(invoke, TASK)
    await _scaffold(invoke, "--role", "architect")
    await _scaffold(invoke, "--workflow")
    _restamp(_path(project, "workflow.toml"), OLD)
    assert await _entries(invoke) == [
        _entry(TASK, "template", __version__, "current"),
        _entry("architect", "role", __version__, "current"),
        _entry("workflow", "workflow", OLD, "drifted"),
    ]


@pytest.mark.covers("override list", "--json")
async def test_list_json_still_prints_a_broken_override_and_exits_1(project, invoke) -> None:
    _path(project, f"templates/{FEATURE}").parent.mkdir(parents=True)
    _path(project, f"templates/{FEATURE}").write_text("no markers here", encoding="utf-8")
    result = await invoke(["override", "list", "--json"])
    assert result.exit_code == 1
    assert result.output == (
        '[\n  {\n    "name": "items/feature.md.j2",\n    "kind": "template",\n'
        '    "base_version": null,\n    "state": "broken"\n  }\n]\n'
    )


async def test_list_says_when_there_are_no_overrides(project, invoke) -> None:
    result = await invoke(["override", "list"])
    assert (result.exit_code, result.output) == (
        0,
        "no overrides found under .overrides/\nRun sq override scaffold <template_name> to start "
        "one.\n",
    )


async def test_list_prints_a_table_and_the_cause_of_an_unreadable_override(project, invoke) -> None:
    await _scaffold(invoke, "--playbook")
    _restamp(_path(project, "playbook.toml"), OLD)
    broken = _path(project, f"templates/{TASK}")
    _break_utf8(broken)
    result = await invoke(["override", "list"])
    assert result.exit_code == 1
    assert result.output.splitlines() == [
        "Name              Kind      Base Version  State  ",
        "items/task.md.j2  template  (unstamped)   broken ",
        "playbook          playbook  0.16.0        drifted",
        NOT_UTF8.format(path=broken).rstrip("\n"),
    ]


# ------------------------------------------------------------------------------------- diff


@pytest.mark.covers("override diff", "NAME")
async def test_diff_names_a_template_and_compares_it_with_the_bundled_default(
    project, invoke
) -> None:
    await _drift(invoke, project, TASK, path=f"templates/{TASK}", version=OLD_TEMPLATE)
    await _bystander(invoke, project, workflow=True)
    (diffed,) = await _diff(invoke, TASK)
    upgrade = diffed.pop("delta_upgrade")
    mine = diffed.pop("delta_mine")
    assert diffed == {
        "name": TASK,
        "kind": "template",
        "base_version": OLD_TEMPLATE,
        "base_available": True,
    }
    assert mine.splitlines()[:2] == [
        f"--- bundled/{TASK}",
        f"+++ .overrides/templates/{TASK}",
    ]
    assert _changes(mine) == [f"+<!-- squads:override-base:{OLD_TEMPLATE} -->"]
    assert upgrade.splitlines()[:2] == [
        f"--- bundled/{TASK}@v{OLD_TEMPLATE}",
        f"+++ bundled/{TASK} (current)",
    ]
    assert _changes(upgrade) == ["-<!-- sq:summary -->", "-<!-- sq:summary:end -->", "-"]


@pytest.mark.covers("override diff", "--role")
async def test_diff_role_compares_the_role_file_with_the_bundled_role(project, invoke) -> None:
    await _drift(invoke, project, "--role", "architect", path="roles/architect.toml")
    await _bystander(invoke, project)
    (diffed,) = await _diff(invoke, "--role", "architect")
    upgrade = diffed.pop("delta_upgrade")
    mine = diffed.pop("delta_mine")
    assert diffed == {
        "name": "architect",
        "kind": "role",
        "base_version": OLD,
        "base_available": True,
    }
    assert mine.splitlines()[:2] == [
        "--- bundled/roles.toml#architect",
        "+++ .overrides/roles/architect.toml",
    ]
    assert upgrade.splitlines()[:2] == [
        f"--- bundled/roles.toml@v{OLD}",
        "+++ bundled/roles.toml (current)",
    ]


@pytest.mark.covers("override diff", "--workflow")
async def test_diff_workflow_compares_the_workflow_file_with_the_bundled_spec(
    project, invoke
) -> None:
    await _drift(invoke, project, "--workflow", path="workflow.toml")
    await _bystander(invoke, project)
    (diffed,) = await _diff(invoke, "--workflow")
    upgrade = diffed.pop("delta_upgrade")
    mine = diffed.pop("delta_mine")
    assert diffed == {
        "name": "workflow",
        "kind": "workflow",
        "base_version": OLD,
        "base_available": True,
    }
    assert mine.splitlines()[:2] == ["--- bundled/workflow.toml", "+++ .overrides/workflow.toml"]
    assert upgrade.splitlines()[:2] == [
        f"--- bundled/workflow.toml@v{OLD}",
        "+++ bundled/workflow.toml (current)",
    ]


@pytest.mark.covers("override diff", "--playbook")
async def test_diff_playbook_compares_the_playbook_file_with_the_bundled_playbook(
    project, invoke
) -> None:
    await _drift(invoke, project, "--playbook", path="playbook.toml")
    await _bystander(invoke, project)
    (diffed,) = await _diff(invoke, "--playbook")
    upgrade = diffed.pop("delta_upgrade")
    mine = diffed.pop("delta_mine")
    assert diffed == {
        "name": "playbook",
        "kind": "playbook",
        "base_version": OLD,
        "base_available": True,
    }
    assert mine.splitlines()[:2] == ["--- bundled/playbook.toml", "+++ .overrides/playbook.toml"]
    assert upgrade.splitlines()[:2] == [
        f"--- bundled/playbook.toml@v{OLD}",
        "+++ bundled/playbook.toml (current)",
    ]


@pytest.mark.covers("override diff", "--roles-catalog")
async def test_diff_roles_catalog_compares_the_catalog_file_with_the_bundled_catalog(
    project, invoke
) -> None:
    await _drift(invoke, project, "--roles-catalog", path="roles.toml")
    await _bystander(invoke, project)
    (diffed,) = await _diff(invoke, "--roles-catalog")
    upgrade = diffed.pop("delta_upgrade")
    mine = diffed.pop("delta_mine")
    assert diffed == {
        "name": "roles",
        "kind": "roles",
        "base_version": OLD,
        "base_available": True,
    }
    assert mine.splitlines()[:2] == ["--- bundled/roles.toml", "+++ .overrides/roles.toml"]
    assert upgrade.splitlines()[:2] == [
        f"--- bundled/roles.toml@v{OLD}",
        "+++ bundled/roles.toml (current)",
    ]


@pytest.mark.covers("override diff", "--json")
async def test_diff_without_a_name_covers_only_the_drifted_overrides(project, invoke) -> None:
    await _scaffold(invoke, TASK)
    await _scaffold(invoke, FEATURE)
    _restamp(_path(project, f"templates/{TASK}"), OLD_TEMPLATE)
    diffed = await _diff(invoke)
    assert [(d["name"], d["base_version"]) for d in diffed] == [(TASK, OLD_TEMPLATE)]
    assert [list(d) for d in diffed] == [
        ["name", "kind", "base_version", "base_available", "delta_mine", "delta_upgrade"]
    ]


async def test_diff_without_a_name_says_when_nothing_drifted(project, invoke) -> None:
    await _scaffold(invoke, TASK)
    result = await invoke(["override", "diff"])
    assert (result.exit_code, result.output) == (0, "no drifted overrides found\n")


async def test_diff_prints_both_deltas_under_the_override_name(project, invoke) -> None:
    await _scaffold(invoke, "--playbook")
    result = await invoke(["override", "diff", "playbook"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[:5] == [
        "",
        "Override: playbook  (kind: playbook)",
        f"base version: v{__version__}",
        "",
        "Δ-mine  (your override vs current bundled):",
    ]
    assert lines[5:7] == ["--- bundled/playbook.toml", "+++ .overrides/playbook.toml"]
    assert lines[-3:] == [
        "",
        "Δ-upgrade  (base-version bundled vs current bundled — what the upgrade changed):",
        "(no difference)",
    ]


async def test_diff_without_a_name_names_a_broken_override_and_exits_1_after_the_rest(
    project, invoke
) -> None:
    await _scaffold(invoke, TASK)
    _restamp(_path(project, f"templates/{TASK}"), OLD_TEMPLATE)
    _path(project, f"templates/{FEATURE}").write_text("no markers here", encoding="utf-8")
    broken = _path(project, "templates/items/story.md.j2")
    _break_utf8(broken)
    expected = [
        "error: items/feature.md.j2 is broken (a required sq region is missing); run "
        "`sq override list` for the state of every override",
        NOT_UTF8.format(path=broken).rstrip("\n"),
    ]
    result = await invoke(["override", "diff", "--json"])
    assert result.exit_code == 1
    assert result.output.splitlines()[:2] == expected
    result = await invoke(["override", "diff"])
    assert result.exit_code == 1
    assert result.output.splitlines()[-2:] == expected


async def test_diff_refuses_an_override_that_is_not_there(project, invoke) -> None:
    for args, line in (
        (["nope"], "no template override for 'nope' (run `sq override scaffold nope` first)"),
        (
            ["--role", "ghost"],
            "no role override for 'ghost' (run `sq override scaffold --role ghost` first)",
        ),
        (
            ["workflow"],
            "no workflow override found (run `sq override scaffold workflow` first)",
        ),
        (
            ["--playbook"],
            "no playbook override found (run `sq override scaffold playbook` first)",
        ),
        (
            ["roles"],
            "no role catalog override found (run `sq override scaffold roles` first)",
        ),
    ):
        result = await invoke(["override", "diff", *args])
        assert (result.exit_code, result.output) == (1, f"error: {line}\n")


async def test_diff_refuses_an_override_file_that_is_not_utf8(project, invoke) -> None:
    broken = _path(project, f"templates/{TASK}")
    _break_utf8(broken)
    result = await invoke(["override", "diff", TASK])
    assert (result.exit_code, result.output) == (1, NOT_UTF8.format(path=broken))


# ----------------------------------------------------------------------------------- update


@pytest.mark.covers("override update", "NAME")
async def test_update_restamps_the_named_template_and_keeps_its_content(project, invoke) -> None:
    await _drift(invoke, project, TASK, path=f"templates/{TASK}", version=OLD_TEMPLATE)
    await _bystander(invoke, project, workflow=True)
    with _path(project, f"templates/{TASK}").open("a", encoding="utf-8") as handle:
        handle.write("my own line\n")
    result = await invoke(["override", "update", TASK])
    assert (result.exit_code, result.output) == (
        0,
        f"re-stamped {TASK} → v{__version__}\n\nRun sq check to confirm the drift warning is "
        "cleared.\n",
    )
    assert await _entries(invoke) == [
        _entry(TASK, "template", __version__, "current"),
        _entry("workflow", "workflow", OLD, "drifted"),
    ]
    (diffed,) = await _diff(invoke, TASK)
    assert _changes(diffed["delta_mine"]) == [f"+{STAMP}", "+my own line"]


@pytest.mark.covers("override update", "--role")
async def test_update_role_restamps_the_role_file(project, invoke) -> None:
    await _drift(invoke, project, "--role", "architect", path="roles/architect.toml")
    await _bystander(invoke, project)
    result = await invoke(["override", "update", "--role", "architect"])
    assert (result.exit_code, result.output) == (
        0,
        f"re-stamped architect → v{__version__}\n\nRun sq check to confirm the drift warning is "
        "cleared.\n",
    )
    assert await _entries(invoke) == [
        _entry(TASK, "template", OLD_TEMPLATE, "drifted"),
        _entry("architect", "role", __version__, "current"),
    ]


@pytest.mark.covers("override update", "--workflow")
async def test_update_workflow_restamps_the_workflow_file(project, invoke) -> None:
    await _drift(invoke, project, "--workflow", path="workflow.toml")
    await _bystander(invoke, project)
    result = await invoke(["override", "update", "--workflow"])
    assert (result.exit_code, result.output) == (
        0,
        f"re-stamped workflow → v{__version__}\n\nRun sq check to confirm the drift warning is "
        "cleared.\n",
    )
    assert await _entries(invoke) == [
        _entry(TASK, "template", OLD_TEMPLATE, "drifted"),
        _entry("workflow", "workflow", __version__, "current"),
    ]


@pytest.mark.covers("override update", "--playbook")
async def test_update_playbook_restamps_the_playbook_file(project, invoke) -> None:
    await _drift(invoke, project, "--playbook", path="playbook.toml")
    await _bystander(invoke, project)
    result = await invoke(["override", "update", "--playbook"])
    assert (result.exit_code, result.output) == (
        0,
        f"re-stamped playbook → v{__version__}\n\nRun sq check to confirm the drift warning is "
        "cleared.\n",
    )
    assert await _entries(invoke) == [
        _entry(TASK, "template", OLD_TEMPLATE, "drifted"),
        _entry("playbook", "playbook", __version__, "current"),
    ]


@pytest.mark.covers("override update", "--roles-catalog")
async def test_update_roles_catalog_restamps_the_catalog_file(project, invoke) -> None:
    await _drift(invoke, project, "--roles-catalog", path="roles.toml")
    await _bystander(invoke, project)
    result = await invoke(["override", "update", "--roles-catalog"])
    assert (result.exit_code, result.output) == (
        0,
        f"re-stamped roles → v{__version__}\n\nRun sq check to confirm the drift warning is "
        "cleared.\n",
    )
    assert await _entries(invoke) == [
        _entry(TASK, "template", OLD_TEMPLATE, "drifted"),
        _entry("roles", "roles", __version__, "current"),
    ]


async def test_update_without_a_name_restamps_every_valid_override(project, invoke) -> None:
    await _drift(invoke, project, TASK, path=f"templates/{TASK}", version=OLD_TEMPLATE)
    await _drift(invoke, project, "--workflow", path="workflow.toml")
    result = await invoke(["override", "update"])
    assert (result.exit_code, result.output) == (
        0,
        f"re-stamped {TASK} → v{__version__}\nre-stamped workflow → v{__version__}\n\n"
        "Run sq check to confirm the drift warning is cleared.\n",
    )
    assert await _entries(invoke) == [
        _entry(TASK, "template", __version__, "current"),
        _entry("workflow", "workflow", __version__, "current"),
    ]


async def test_update_without_a_name_skips_an_unreadable_override_and_exits_1(
    project, invoke
) -> None:
    await _drift(invoke, project, "--workflow", path="workflow.toml")
    broken = _path(project, f"templates/{TASK}")
    _break_utf8(broken)
    result = await invoke(["override", "update"])
    assert result.exit_code == 1
    assert result.output == (
        f"re-stamped workflow → v{__version__}\n\nRun sq check to confirm the drift warning is "
        f"cleared.\n{NOT_UTF8.format(path=broken)}"
    )
    listed = await invoke(["override", "list", "--json"])
    assert [(e["name"], e["state"]) for e in json.loads(listed.output)] == [
        (TASK, "broken"),
        ("workflow", "current"),
    ]


async def test_update_without_a_name_names_the_unreadable_override_when_nothing_else_is_valid(
    project, invoke
) -> None:
    broken = _path(project, f"templates/{TASK}")
    _break_utf8(broken)
    result = await invoke(["override", "update"])
    assert (result.exit_code, result.output) == (1, NOT_UTF8.format(path=broken))


async def test_update_without_a_name_says_when_there_is_nothing_to_update(project, invoke) -> None:
    result = await invoke(["override", "update"])
    assert (result.exit_code, result.output) == (
        0,
        "nothing to update (no overrides found, or all are current)\n",
    )


async def test_update_refuses_an_override_that_is_not_there(project, invoke) -> None:
    for args, line in (
        (
            ["nope"],
            "no override found for 'nope' (kind='template'). Run `sq override list` to see "
            "existing overrides.",
        ),
        (
            ["--role", "ghost"],
            "no override found for 'ghost' (kind='role'). Run `sq override list` to see "
            "existing overrides.",
        ),
        (["--workflow"], "no workflow override found. Run `sq override scaffold workflow` first."),
        (["--playbook"], "no playbook override found. Run `sq override scaffold playbook` first."),
        (
            ["--roles-catalog"],
            "no role catalog override found. Run `sq override scaffold roles` first.",
        ),
    ):
        result = await invoke(["override", "update", *args])
        assert (result.exit_code, result.output) == (1, f"error: {line}\n")


async def test_update_refuses_a_template_that_lost_its_required_markers(project, invoke) -> None:
    _path(project, f"templates/{FEATURE}").parent.mkdir(parents=True)
    _path(project, f"templates/{FEATURE}").write_text("no markers here", encoding="utf-8")
    result = await invoke(["override", "update", FEATURE])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot re-stamp 'items/feature.md.j2': override is missing required sq markers. "
        "Fix the marker structure first, then run `sq override update`.\n",
    )
    (diffed,) = await _diff(invoke, FEATURE)
    assert _changes(diffed["delta_mine"])[-1] == "+no markers here"


async def test_update_refuses_an_override_file_that_is_not_utf8(project, invoke) -> None:
    broken = _path(project, f"templates/{TASK}")
    _break_utf8(broken)
    result = await invoke(["override", "update", TASK])
    assert (result.exit_code, result.output) == (1, NOT_UTF8.format(path=broken))


# -------------------------------------------------------------------------------------- json


@pytest.mark.covers("override scaffold", "--json")
async def test_scaffold_json_prints_the_override_written(project, invoke) -> None:
    result = await invoke(["override", "scaffold", "--role", "architect", "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps(
            {
                "entry": {
                    "kind": "role",
                    "name": "architect",
                    "path": str(_path(project, "roles/architect.toml")),
                },
                "prefilled": True,
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.covers("override update", "--json")
async def test_update_json_prints_the_overrides_restamped_and_the_unreadable_ones(
    project, invoke
) -> None:
    await _drift(invoke, project, TASK, path=f"templates/{TASK}", version=OLD_TEMPLATE)
    broken = _path(project, f"templates/{FEATURE}")
    _break_utf8(broken)
    result = await invoke(["override", "update", "--json"])
    assert result.exit_code == 1
    assert (
        result.stdout
        == json.dumps(
            {
                "stamped": [TASK],
                "version": __version__,
                "errors": [NOT_UTF8.format(path=broken)[7:-1]],
            },
            indent=2,
        )
        + "\n"
    )
    assert result.stderr == NOT_UTF8.format(path=broken)
