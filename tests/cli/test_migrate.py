"""`sq migrate`: running the pending migrations, reading the changelog, and the bulk
renames of a status, a type and the item-number padding."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._models._schema import SCHEMA_VERSION
from tests.cli import _bundled_documents as documents
from tests.cli._output import json_text, printed

pytestmark = pytest.mark.anyio

OLD_SQUAD = Path(__file__).parents[1] / "fixtures" / "corpus" / "v0_14"
CHECK_HINT = "  run `sq check` to verify integrity\n"
NO_SQUAD = "error: no .squads.toml found in this or any parent directory — run `sq init`\n"


async def _shown(invoke, item_type: str, number: int) -> dict[str, Any]:
    """The `show --json` object of the item *item_type* *number*."""
    result = await invoke([item_type, str(number), "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# ------------------------------------------------------------------------------------- up


@pytest.mark.covers("migrate up")
async def test_up_on_a_current_squad_has_nothing_to_migrate(project, invoke) -> None:
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (
        0,
        f"already at schema v{SCHEMA_VERSION}; nothing to migrate\n",
    )


@pytest.mark.covers("migrate up")
async def test_up_brings_an_older_squad_to_the_current_schema(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(OLD_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    refused = await invoke(["list"])
    assert (refused.exit_code, refused.output) == (
        1,
        f"error: this squad is at schema v0.14; squads {__version__} expects v{SCHEMA_VERSION}. "
        "Run sq migrate up to upgrade it (see `sq migrate help`).\n",
    )
    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert (
        f"migrated to schema v{SCHEMA_VERSION}; index rebuilt — run `sq sync` to regenerate the "
        "agent files (pointers, skills, CLAUDE.md/AGENTS.md sections)"
    ) in lines
    listed = await invoke(["list", "--json"])
    assert listed.exit_code == 0, listed.output
    assert [i["id"] for i in json.loads(listed.output)][:6] == [
        "ROLE-1",
        "FEAT-2",
        "TASK-3",
        "BUG-4",
        "ADR-5",
        "REV-6",
    ]
    again = await invoke(["migrate", "up"])
    assert (again.exit_code, again.output) == (
        0,
        f"already at schema v{SCHEMA_VERSION}; nothing to migrate\n",
    )


@pytest.mark.covers("migrate up")
async def test_up_refuses_a_squad_newer_than_the_package(project, invoke) -> None:
    config = project.root / ".squads.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "9.0"'
        ),
        encoding="utf-8",
    )
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: this squad is at schema v9.0, newer than squads {__version__} "
        f"(v{SCHEMA_VERSION}). Upgrade the squads package.\n",
    )


@pytest.mark.covers("migrate up")
async def test_up_refuses_a_directory_with_no_squad(invoke) -> None:
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (1, NO_SQUAD)


# ---------------------------------------------------------------------------- help and chlog


@pytest.mark.covers("migrate help")
async def test_help_lists_the_migrations_oldest_first_outside_any_squad(invoke) -> None:
    result = await invoke(["migrate", "help"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0].strip() == "migration changelog — read steps with `sq migrate chlog vA..vB`"
    assert [c.strip() for c in lines[2].strip("┃").split("┃")] == [
        "Release",
        "Schema",
        "Summary",
        "Manual",
    ]
    rows = [ln.strip("│").split("│") for ln in lines if ln.startswith("│ v")]
    releases = [tuple(int(n) for n in row[0].strip().lstrip("v").split(".")) for row in rows]
    assert releases[0] == (0, 2, 0)
    assert releases == sorted(releases)
    assert rows[-1][1].strip().endswith(f"→v{SCHEMA_VERSION}")


@pytest.mark.covers("migrate chlog", "vFROM..vTO")
async def test_chlog_prints_the_manual_steps_of_each_migration_in_the_range(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.1.1..v0.2.0"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0].rstrip() == "v0.2.0 — manual steps (schema v0.1→v0.2)"
    assert [ln for ln in lines if "manual steps (schema" in ln] == [lines[0]]


@pytest.mark.covers("migrate chlog", "vFROM..vTO")
async def test_chlog_says_so_when_the_range_holds_no_manual_step(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.10.0..v0.11.0"])
    assert (result.exit_code, result.output) == (0, "no manual steps for v0.10.0..v0.11.0\n")


@pytest.mark.covers("migrate chlog", "vFROM..vTO")
async def test_chlog_refuses_a_range_without_two_dots(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.2.0"])
    assert (result.exit_code, result.output) == (
        1,
        "error: expected a range like v0.1.1..v0.2.0 (vFROM..vTO, FROM below TO), got 'v0.2.0'\n",
    )


@pytest.mark.covers("migrate chlog", "vFROM..vTO")
@pytest.mark.parametrize(
    "span", ["a..b", "v1x..v2y", "v0.1.0..v0.2.0..v0.3.0", "v0.17.0..v0.1.0", "v0.2.0..v0.2.0"]
)
async def test_chlog_refuses_a_bound_that_is_no_version_or_a_range_not_ascending(
    invoke, span
) -> None:
    result = await invoke(["migrate", "chlog", span])
    assert (result.exit_code, result.output) == (
        1,
        f"error: expected a range like v0.1.1..v0.2.0 (vFROM..vTO, FROM below TO), got {span!r}\n",
    )


@pytest.mark.covers("migrate chlog", "vFROM..vTO")
async def test_chlog_requires_a_range(invoke) -> None:
    result = await invoke(["migrate", "chlog"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq migrate chlog [OPTIONS] vFROM..vTO\n"
        "Try 'sq migrate chlog --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'vFROM..vTO'.                                               │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


# --------------------------------------------------------------------------- rename-status


@pytest.mark.covers("migrate rename-status", "TYPE")
@pytest.mark.covers("migrate rename-status", "OLD_STATUS")
@pytest.mark.covers("migrate rename-status", "NEW_STATUS")
async def test_rename_status_relabels_the_items_of_the_type_at_that_status(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "task", "Draft", "Ready"])
    assert (result.exit_code, result.output) == (
        0,
        "rename-status done: task: Draft → Ready, 1 item(s) renamed\n" + CHECK_HINT,
    )
    assert (await _shown(invoke, "task", 3))["status"] == "Ready"
    assert (await _shown(invoke, "feature", 2))["status"] == "Draft"


@pytest.mark.covers("migrate rename-status", "OLD_STATUS")
async def test_rename_status_refuses_a_status_outside_the_lifecycle(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "task", "Draft", "Bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'Bogus' is not a state of task's lifecycle "
        "(states: Blocked, Cancelled, Done, Draft, InProgress, InReview, Ready)\n",
    )
    assert (await _shown(invoke, "task", 3))["status"] == "Draft"


@pytest.mark.covers("migrate rename-status", "TYPE")
async def test_rename_status_refuses_a_type_the_spec_does_not_declare(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "nosuch", "Draft", "Ready"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'nosuch' is not declared in the active spec\n",
    )


# ----------------------------------------------------------------------------- rename-type


@pytest.mark.covers("migrate rename-type", "OLD_TYPE")
@pytest.mark.covers("migrate rename-type", "NEW_TYPE")
async def test_rename_type_moves_the_items_to_the_new_type_and_prefix(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "task", "bug"])
    assert (result.exit_code, result.output) == (
        0,
        "rename-type done: task → bug, 1 item(s) renamed; index rebuilt\n" + CHECK_HINT,
    )
    moved = await _shown(invoke, "bug", 3)
    assert (moved["id"], moved["title"], moved["parent"]) == (
        "BUG-3",
        "Build the query parser",
        "FEAT-2",
    )
    assert [s["local_id"] for s in moved["subentities"]] == ["ST1", "ST2"]


@pytest.mark.covers("migrate rename-type", "OLD_TYPE")
async def test_rename_type_refuses_a_roster_type(populated_project, invoke) -> None:
    result = await invoke(["migrate", "rename-type", "task", "role"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'role' is a reserved roster type (role/skill/operator) and cannot be renamed\n",
    )


@pytest.mark.covers("migrate rename-type", "OLD_TYPE", "NEW_TYPE")
async def test_rename_type_refuses_to_rename_a_type_to_itself(populated_project, invoke) -> None:
    result = await invoke(["migrate", "rename-type", "task", "task"])
    assert (result.exit_code, result.output) == (1, "error: cannot rename 'task' to itself\n")


@pytest.mark.covers("migrate rename-type", "OLD_TYPE")
async def test_rename_type_refuses_a_type_the_spec_does_not_declare(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "task", "nosuch"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'nosuch' is not declared in the active spec\n",
    )


@pytest.mark.covers("migrate rename-type", "NEW_TYPE")
async def test_rename_type_refuses_a_move_that_leaves_a_child_with_an_invalid_parent(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "feature", "bug"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename feature to bug: child item(s) TASK-3 would have an invalid "
        "parent type. Re-parent or remove those children first.\n",
    )
    assert (await _shown(invoke, "feature", 2))["id"] == "FEAT-2"


# ---------------------------------------------------------------------------------- repad


@pytest.mark.covers("migrate repad", "WIDTH")
async def test_repad_widens_the_item_files_numbers_and_leaves_the_ids(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "repad", "8"])
    assert (result.exit_code, result.output) == (
        0,
        "repad done: padding 6 → 8; 4 file(s) renamed; index rebuilt\n" + CHECK_HINT,
    )
    task = await _shown(invoke, "task", 3)
    assert (task["id"], task["path"]) == ("TASK-3", "tasks/TASK-00000003-build-the-query-parser.md")


@pytest.mark.covers("migrate repad", "WIDTH")
async def test_repad_refuses_a_width_that_does_not_exceed_the_current_one(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "repad", "6"])
    assert (result.exit_code, result.output) == (
        1,
        "error: new padding 6 must be greater than the current padding 6; padding can only "
        "increase (one-way format bump)\n",
    )
    task = await _shown(invoke, "task", 3)
    assert task["path"] == "tasks/TASK-000003-build-the-query-parser.md"


@pytest.mark.covers("migrate repad", "WIDTH")
async def test_repad_refuses_a_width_above_the_maximum_and_renames_nothing(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "repad", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: new padding 99 is above the maximum of 32 digits; padding can only increase, "
        "so a width that wide could not be taken back\n",
    )
    task = await _shown(invoke, "task", 3)
    assert task["path"] == "tasks/TASK-000003-build-the-query-parser.md"


@pytest.mark.covers("migrate repad", "WIDTH")
async def test_repad_refuses_a_width_that_is_not_an_integer(populated_project, invoke) -> None:
    result = await invoke(["migrate", "repad", "wide"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq migrate repad [OPTIONS] WIDTH\nTry 'sq migrate repad --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Invalid value for 'WIDTH': 'wide' is not a valid integer.                    │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("migrate help", "--json")
async def test_help_json_lists_each_migration_with_its_manual_steps(invoke) -> None:
    output = await printed(invoke, ["migrate", "help", "--json"])
    assert output == json_text(documents.MIGRATIONS)


@pytest.mark.covers("migrate chlog", "--json")
async def test_chlog_json_prints_the_range_and_its_migrations_with_manual_steps(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.10.0..v0.11.0", "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps(
            {"from_version": "0.10.0", "to_version": "0.11.0", "migrations": []}, indent=2
        )
        + "\n"
    )


@pytest.mark.covers("migrate up", "--json")
async def test_up_json_reports_each_migration_run_on_an_older_squad(
    tmp_path, monkeypatch, invoke
) -> None:
    monkeypatch.chdir(shutil.copytree(OLD_SQUAD, tmp_path / "old"))
    result = await invoke(["migrate", "up", "--json"])
    shipped = {m["version"]: m for m in documents.MIGRATIONS["migrations"]}

    def applied(version: str, changed: int, reports: list[str]) -> dict[str, Any]:
        entry = shipped[version]
        return {
            "version": version,
            "from_schema": entry["from_schema"],
            "to_schema": entry["to_schema"],
            "summary": entry["summary"],
            "changed": changed,
            "reports": reports,
            "skipped": [],
            "manual": bool(entry["manual"]),
        }

    assert (result.exit_code, result.output) == (
        0,
        json_text(
            {
                "schema_version": SCHEMA_VERSION,
                "applied": [
                    applied("0.15.0", 6, []),
                    applied(
                        "0.16.0",
                        5,
                        [
                            "0 comment header(s) rewritten in 0 file(s); 0 already carried a slug",
                            "5 file(s) flattened; 0 key(s) lifted (none); 0 skill description(s) "
                            "dropped; 2 `path:` key(s) removed",
                            "0 operator title(s) set from the stored full name",
                            "0 dropped skill description(s) differed from the one kept",
                            "1 role(s) stamped origin project",
                            "4 skill(s) stamped origin system",
                            "4 skill(s) given a discussion region",
                        ],
                    ),
                    applied(
                        "0.17.0",
                        0,
                        [
                            "dev-agent: no catalog entry and no role file; define it with "
                            "`sq role dev-agent update --job-title … --desc … --mission …`"
                        ],
                    ),
                ],
                "reconciled": {"indexed": [], "missing": []},
                "config_dropped": ["squads_version"],
                "notice": "stripped retired regions from 3 item files — review the diff",
                "unreadable": [],
                "manual_span": "v0.14.0..v0.17.0",
            }
        ),
    )


@pytest.mark.covers("migrate repad", "--json")
async def test_repad_json_prints_the_padding_before_and_after(populated_project, invoke) -> None:
    result = await invoke(["migrate", "repad", "8", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text({"previous": 6, "width": 8, "renamed": 4}),
    )


@pytest.mark.covers("migrate rename-type", "--json")
async def test_rename_type_json_prints_the_items_moved_and_their_new_ids(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "task", "bug", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text(
            {
                "old_type": "task",
                "new_type": "bug",
                "renamed": 1,
                "ids": [{"old": "TASK-3", "new": "BUG-3"}],
            }
        ),
    )


@pytest.mark.covers("migrate rename-status", "--json")
async def test_rename_status_json_prints_how_many_items_were_relabelled(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "task", "Draft", "Ready", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text({"type": "task", "old_status": "Draft", "new_status": "Ready", "renamed": 1}),
    )
