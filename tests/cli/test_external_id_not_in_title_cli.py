"""`external_id_not_in_title` at the CLI: `sq check` exits 0 at `warn` and 3 at `@error` and prints
a pattern and a title with square brackets intact; `sq create` is refused (exit 1) only at
`@error`; `sq workflow lint` refuses an uncompilable pattern, a reserved `@` and a roster
selection; a basic TOML string with a single backslash fails in the TOML parser first.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import TRACKER_KEY, TypeRow, override_toml, service_with, write_override

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_NAME = "external_id_not_in_title"


_BRACKETED = r"\[[A-Z]+-\d+\]"


@pytest.mark.parametrize(
    ("suffix", "exit_code", "level"), [("", 0, "warn"), ("@error", 3, "error")]
)
async def test_check_exit_code_follows_the_level_and_the_json_names_the_match(
    project, invoke, suffix: str, exit_code: int, level: str
) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(unselected, "task", "[ABC-1] a bracketed key")).item
    service_with(project.squad_dir, override_toml(_TASK, (f"{_NAME}:{_BRACKETED}{suffix}",)))

    checked = await invoke(["check"])
    assert checked.exit_code == exit_code, checked.output
    assert "`[ABC-1]`" in checked.output
    rows = json.loads((await invoke(["check", "--json"])).output)
    found = [r for r in rows if "external-id" in r.get("message", "")]
    assert [(r["item"], r["level"]) for r in found] == [(item.id, level)]
    assert f"`{_BRACKETED}`" in found[0]["message"]


@pytest.mark.xfail(
    strict=True,
    reason="the console print drops a backslash that precedes a square bracket in a message",
)
async def test_check_text_shows_a_pattern_with_an_escaped_bracket_intact(project, invoke) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    await create_item(unselected, "task", "[ABC-1] a bracketed key")
    service_with(project.squad_dir, override_toml(_TASK, (f"{_NAME}:{_BRACKETED}",)))
    checked = await invoke(["check"])
    assert f"`{_BRACKETED}`" in checked.output.replace("\n", "")


@pytest.mark.parametrize(("suffix", "create_exit"), [("", 0), ("@error", 1)])
async def test_create_is_refused_only_at_error(
    project, invoke, suffix: str, create_exit: int
) -> None:
    service_with(project.squad_dir, override_toml(_TASK, (f"{_NAME}:{TRACKER_KEY}{suffix}",)))
    created = await invoke(["create", "task", "Fix ABC-1", "--author", "manager"])
    assert created.exit_code == create_exit, created.output
    clean = await invoke(["create", "task", "Fix it", "--author", "manager"])
    assert clean.exit_code == 0, clean.output


@pytest.mark.parametrize(
    ("toml", "needle"),
    [
        (f"[items.task]\nvalidators = ['{_NAME}:[abc']\n", "regular"),
        (f"[items.task]\nvalidators = ['{_NAME}:user@host']\n", "separates"),
        (f'[items.task]\nvalidators = ["{_NAME}"]\n', "required"),
        (f"[items.role]\nvalidators = ['{_NAME}:{TRACKER_KEY}']\n", "roster"),
    ],
    ids=["uncompilable", "reserved-at", "missing", "roster"],
)
async def test_lint_refuses_a_bad_entry(project, invoke, toml: str, needle: str) -> None:
    write_override(project.squad_dir, toml)
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert needle in linted.output


async def test_a_basic_toml_string_with_a_single_backslash_fails_in_the_toml_parser(
    project, invoke
) -> None:
    write_override(project.squad_dir, f'[items.task]\nvalidators = ["{_NAME}:[A-Z]+-\\d+"]\n')
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert "Malformed" in linted.output


async def test_lint_refuses_a_warning_pattern_however_often_it_runs(project, invoke) -> None:
    write_override(project.squad_dir, f"[items.task]\nvalidators = ['{_NAME}:[[a]]']\n")
    for _ in range(2):
        linted = await invoke(["workflow", "lint"])
        assert linted.exit_code == 1, linted.output
        assert "warning" in linted.output
    listed = await invoke(["list"])
    assert listed.exit_code == 1, listed.output
