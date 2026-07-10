"""`sq show` rendering: on a TTY the body renders as styled markdown (Rich strips the leading
`##`), `--raw` opts back out, piped output is plain and byte-stable, `--json` is unaffected
by any render flag; root `sq show` resolves by full id/bare number/any type and errors
cleanly on an unknown id or a wrong type prefix; the default view includes each sub-entity's
roll-up summary table and (with `--comments`) the discussion; `--full` adds one pane per
sub-entity with its body, omits comments unless `--comments` is also given (which then
orders sub-entity comments before the main discussion), and degrades gracefully with no
sub-entities; a bracket-bearing title/comment-author never leaks a Rich-escape backslash on
either the plain or the styled path. `sq role|skill|operator show` share the same body-render
path. This is the one home for `sq show`'s rendered (non-JSON) output — the raw item/
sub-entity *template* render path (markers, findings legend, scaffold hints) is proven
independently in tests/unit/test_item_and_subentity_templates_render_structurally.py.
"""

import json

import pytest

from squads._cli import _common

pytestmark = pytest.mark.anyio


@pytest.fixture
def styled(monkeypatch):
    """Patch _is_styled() so the TTY (Rich Markdown) render path is exercised."""
    monkeypatch.setattr(_common, "_is_styled", lambda: True)


async def test_tty_show_renders_markdown_and_raw_preserves_the_literal_markers(
    project, styled, invoke
) -> None:
    await invoke(
        [
            "create",
            "task",
            "Styled",
            "--author",
            "manager",
            "-m",
            "## Section\n\nBold **word** here.\n\n```python\nx = 1\n```",
        ]
    )
    styled_out = await invoke(["task", "2", "show"])
    assert styled_out.exit_code == 0, styled_out.output
    assert "## Section" not in styled_out.output
    assert "Section" in styled_out.output
    assert "x = 1" in styled_out.output

    raw_out = await invoke(["task", "2", "show", "--raw"])
    assert "## Section" in raw_out.output


async def test_piped_show_is_plain_and_byte_stable_across_two_runs(project, invoke) -> None:
    await invoke(["create", "task", "Plain", "--author", "manager", "-m", "## Heading\n\nBody."])
    r1 = await invoke(["task", "2", "show"])
    r2 = await invoke(["task", "2", "show"])
    assert r1.exit_code == 0
    assert "## Heading" in r1.output and "Body." in r1.output
    assert r1.output == r2.output


async def test_json_output_is_byte_identical_regardless_of_raw_or_comments_flags(
    project, invoke
) -> None:
    await invoke(["create", "task", "JSON test", "--author", "manager", "-m", "Body."])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "A comment."])
    base = await invoke(["task", "2", "show", "--json"])
    raw = await invoke(["task", "2", "show", "--json", "--raw"])
    comments = await invoke(["task", "2", "show", "--json", "--comments"])
    assert base.exit_code == raw.exit_code == comments.exit_code == 0
    assert base.output == raw.output == comments.output
    assert json.loads(base.output)["id"] == "TASK-2"


async def test_root_show_resolves_by_full_id_or_bare_number_for_any_type(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])  # 2
    await invoke(["create", "task", "T", "--author", "manager"])  # 3
    await invoke(["create", "bug", "B", "--author", "manager"])  # 4

    by_id = await invoke(["show", "FEAT-000002"])
    assert by_id.exit_code == 0 and "FEAT-000002" in by_id.output and "F" in by_id.output

    by_number = await invoke(["show", "3"])
    assert by_number.exit_code == 0 and "TASK-000003" in by_number.output


async def test_root_show_errors_cleanly_on_unknown_id_and_wrong_type_prefix(
    project, invoke
) -> None:
    unknown = await invoke(["show", "999"])
    assert unknown.exit_code != 0 and "999" in unknown.output

    await invoke(["create", "feature", "F", "--author", "manager"])
    wrong_prefix = await invoke(["show", "TASK-000002"])
    assert wrong_prefix.exit_code != 0
    assert "FEAT-2" in wrong_prefix.output


async def test_root_show_accepts_raw_json_comments_and_full_flags(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager", "-m", "Body."])
    assert (await invoke(["show", "2", "--raw"])).exit_code == 0
    assert (await invoke(["show", "2", "--json"])).exit_code == 0
    assert (await invoke(["show", "2", "--comments"])).exit_code == 0
    assert (await invoke(["show", "2", "--full"])).exit_code == 0


async def test_default_show_includes_the_subentity_roll_up_summary_table(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "Validate input"])
    await invoke(["task", "2", "add-subtask", "Write tests"])
    r = await invoke(["task", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "ST1" in r.output and "Validate input" in r.output
    assert "ST2" in r.output and "Write tests" in r.output
    assert "Status" in r.output


async def test_comments_flag_renders_discussion_or_the_empty_fallback(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager", "-m", "Body."])
    empty = await invoke(["task", "2", "show", "--comments"])
    assert "no discussion" in empty.output

    await invoke(
        ["task", "2", "comment", "--as", "manager", "-m", "First point.", "-m", "Second point."]
    )
    filled = await invoke(["task", "2", "show", "--comments"])
    assert "First point." in filled.output and "Second point." in filled.output
    assert "---" in filled.output  # plain-mode comment delimiter


async def test_show_never_injects_a_bare_body_label(project, invoke) -> None:
    """Regression: sq show must not print a bare 'Body' literal above the content."""
    await invoke(["create", "task", "Show test", "--author", "manager", "-m", "Content."])
    r = await invoke(["task", "2", "show"])
    lines = r.output.splitlines()
    assert not any(line.strip() == "Body" for line in lines)
    assert "Content." in r.output


async def test_full_flag_shows_subentity_body_panes_and_omits_comments_by_default(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "A subtask"])
    await invoke(["task", "2", "subtask", "1", "body", "-m", "Body of the subtask."])
    await invoke(["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "Sub cmt."])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "Main cmt."])

    r = await invoke(["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    assert "ST1" in r.output
    assert "Body of the subtask." in r.output
    assert "===" in r.output  # plain-mode pane delimiter
    assert "Sub cmt." not in r.output
    assert "Main cmt." not in r.output


async def test_full_comments_orders_subentity_comments_before_the_main_discussion(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "A subtask"])
    await invoke(["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "Per-sub."])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "Main discussion."])
    r = await invoke(["task", "2", "show", "--full", "--comments"])
    assert "Per-sub." in r.output and "Main discussion." in r.output
    assert r.output.index("Per-sub.") < r.output.index("Main discussion.")


async def test_full_degrades_gracefully_with_no_subentities_and_stays_byte_stable(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager", "-m", "Body text."])
    r1 = await invoke(["task", "2", "show", "--full"])
    r2 = await invoke(["task", "2", "show", "--full"])
    assert r1.exit_code == 0
    assert "Body text." in r1.output
    assert "===" not in r1.output
    assert r1.output == r2.output


async def test_full_json_is_unaffected_by_the_full_flag(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "A sub"])
    base = await invoke(["task", "2", "show", "--json"])
    full = await invoke(["task", "2", "show", "--json", "--full"])
    full_comments = await invoke(["task", "2", "show", "--json", "--full", "--comments"])
    assert base.output == full.output == full_comments.output


async def test_full_pane_title_shows_local_id_title_and_status_badge(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "My subtask"])
    r = await invoke(["task", "2", "show", "--full"])
    assert "ST1" in r.output and "My subtask" in r.output and "Todo" in r.output


@pytest.mark.parametrize("styled_render", [False, True])
async def test_bracket_bearing_titles_and_comment_headers_never_leak_an_escape_backslash(
    project, invoke, monkeypatch, styled_render
) -> None:
    if styled_render:
        monkeypatch.setattr(_common, "_is_styled", lambda: True)
    await invoke(["create", "task", "T", "--author", "manager", "-m", "Body."])
    await invoke(["task", "2", "add-subtask", "Danger [red]x[/red] and [x] checkbox"])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "Comment text."])

    r = await invoke(["task", "2", "show", "--full", "--comments"])
    assert "[red]x[/red]" in r.output
    assert "[x]" in r.output
    assert "Comment text." in r.output
    if not styled_render:
        assert r"\[" not in r.output


async def test_role_skill_and_operator_show_render_body_as_styled_markdown_and_raw_preserves_it(
    project, styled, invoke
) -> None:
    await invoke(["operator", "add", "Alice Test"])
    await invoke(["skill", "add", "my-skill", "--desc", "A test skill."])

    role = await invoke(["role", "manager", "show"])
    assert role.exit_code == 0 and "## Working agreements" not in role.output
    assert "Working agreements" in role.output
    role_raw = await invoke(["role", "manager", "show", "--raw"])
    assert "## Working agreements" in role_raw.output

    skill = await invoke(["skill", "3", "show"])
    assert "## Instructions" not in skill.output and "Instructions" in skill.output

    operator = await invoke(["operator", "2", "show"])
    assert "Alice Test" in operator.output and "op-alice" in operator.output


async def test_role_show_of_a_bundled_but_inactive_role_offers_an_activation_hint(
    project, invoke
) -> None:
    r = await invoke(["role", "qa", "show"])
    assert r.exit_code == 0, r.output
    assert "activate" in r.output.lower()
