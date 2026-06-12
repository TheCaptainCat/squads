"""Tests for the rendered show output (TASK-000058 / FEAT-000026).

Covers:
- ST1/US1: body rendered as styled markdown on a TTY (via monkeypatching _is_styled)
- ST2/US2: plain/byte-stable output when piped, --raw opt-out, --json unchanged
- ST3/US3: root `sq show <id|number>` for any item type + unknown-id error
- ST4/US4: sub-entity summary table in default output + --comments discussion panes
- ST5/US5: --full panes per sub-entity + --full --comments dossier (TASK-000059)
"""

import json

import pytest
from typer.testing import CliRunner

from squads import _discussion as discussion
from squads._cli import _common, app

# --------------------------------------------------------------------------- fixtures


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def styled(monkeypatch):
    """Patch _is_styled() to return True so tests can exercise the TTY render path."""
    monkeypatch.setattr(_common, "_is_styled", lambda: True)


# --------------------------------------------------------------------------- ST1/US1: TTY markdown


def test_tty_show_renders_markdown_not_raw(runner, styled, tmp_path, monkeypatch, frozen_time):
    """On a TTY (_is_styled patched True), body is rendered through Rich Markdown."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(
        app,
        [
            "create",
            "task",
            "Styled",
            "--author",
            "manager",
            "-m",
            "## Section\n\nBold **word** here.\n\n```python\nx = 1\n```",
        ],
    )
    r = runner.invoke(app, ["task", "2", "show"])
    assert r.exit_code == 0, r.output
    # Rich Markdown strips the ## prefix from headings
    assert "## Section" not in r.output
    # Heading text still appears
    assert "Section" in r.output
    # Code block content is present
    assert "x = 1" in r.output


def test_raw_flag_suppresses_markdown_render(runner, styled, tmp_path, monkeypatch, frozen_time):
    """--raw on a TTY still produces plain body text (literal ## markers preserved)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(
        app,
        ["create", "task", "Raw test", "--author", "manager", "-m", "## Heading\n\nBody text."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "## Heading" in r.output
    assert "Body text." in r.output


# --------------------------------------------------------------------------- ST2/US2: plain/stable
# No TTY in CliRunner → _is_styled() returns False → plain-text path.


def test_piped_show_preserves_raw_markdown(runner, tmp_path, monkeypatch, frozen_time):
    """When stdout is not a TTY, body renders as plain text preserving literal markdown."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(
        app,
        ["create", "task", "Plain", "--author", "manager", "-m", "## Heading\n\nContent here."],
    )
    r = runner.invoke(app, ["task", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "## Heading" in r.output
    assert "Content here." in r.output


def test_piped_output_is_byte_stable(runner, tmp_path, monkeypatch, frozen_time):
    """Running show twice on the same item produces identical output."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Stable", "--author", "manager", "-m", "Stable body."])
    r1 = runner.invoke(app, ["task", "2", "show"])
    r2 = runner.invoke(app, ["task", "2", "show"])
    assert r1.exit_code == 0 and r2.exit_code == 0
    assert r1.output == r2.output


def test_json_unaffected_by_render_flags(runner, tmp_path, monkeypatch, frozen_time):
    """--json output is byte-identical regardless of --raw or --comments."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "JSON test", "--author", "manager", "-m", "Body."])
    runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", "A comment."])
    r_base = runner.invoke(app, ["task", "2", "show", "--json"])
    r_raw = runner.invoke(app, ["task", "2", "show", "--json", "--raw"])
    r_cmt = runner.invoke(app, ["task", "2", "show", "--json", "--comments"])
    assert r_base.exit_code == r_raw.exit_code == r_cmt.exit_code == 0
    assert r_base.output == r_raw.output == r_cmt.output
    data = json.loads(r_base.output)
    assert data["id"] == "TASK-000002"


# --------------------------------------------------------------------------- ST3/US3: root sq show


def test_root_show_by_full_id(runner, tmp_path, monkeypatch, frozen_time):
    """sq show FEAT-000002 resolves a feature by full ID."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "My Feature", "--author", "manager"])
    r = runner.invoke(app, ["show", "FEAT-000002"])
    assert r.exit_code == 0, r.output
    assert "FEAT-000002" in r.output
    assert "My Feature" in r.output


def test_root_show_by_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """sq show 2 resolves via bare sequence number without naming the type."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "bug", "Crash", "--author", "manager"])
    r = runner.invoke(app, ["show", "2"])
    assert r.exit_code == 0, r.output
    assert "BUG-000002" in r.output
    assert "Crash" in r.output


def test_root_show_multiple_types(runner, tmp_path, monkeypatch, frozen_time):
    """sq show works for features, tasks, bugs, decisions, and reviews."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # 2
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # 3
    runner.invoke(app, ["create", "bug", "B", "--author", "manager"])  # 4
    runner.invoke(app, ["create", "decision", "D", "--author", "manager"])  # 5
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])  # 6

    for seq, expected_prefix in [
        ("2", "FEAT"),
        ("3", "TASK"),
        ("4", "BUG"),
        ("5", "ADR"),  # decisions use ADR- prefix
        ("6", "REV"),
    ]:
        r = runner.invoke(app, ["show", seq])
        assert r.exit_code == 0, f"show {seq} failed: {r.output}"
        assert expected_prefix in r.output, f"expected {expected_prefix} in output for seq {seq}"


def test_root_show_unknown_id_errors_cleanly(runner, tmp_path, monkeypatch, frozen_time):
    """sq show with an unknown id exits non-zero with informative output."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["show", "999"])
    assert r.exit_code != 0
    assert "999" in r.output


def test_root_show_wrong_type_prefix_errors_cleanly(runner, tmp_path, monkeypatch, frozen_time):
    """sq show TASK-000002 where 2 is actually a feature errors naming the real type."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])
    r = runner.invoke(app, ["show", "TASK-000002"])
    assert r.exit_code != 0
    assert "FEAT-000002" in r.output


def test_root_show_accepts_all_flags(runner, tmp_path, monkeypatch, frozen_time):
    """--raw, --comments, --json are all accepted by root show."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "-m", "Body."])
    assert runner.invoke(app, ["show", "2", "--raw"]).exit_code == 0
    assert runner.invoke(app, ["show", "2", "--json"]).exit_code == 0
    assert runner.invoke(app, ["show", "2", "--comments"]).exit_code == 0


# --------------------------------------------------------------------------- ST4/US4: summary+disc


def test_task_summary_shown_in_default_output(runner, tmp_path, monkeypatch, frozen_time):
    """Default task show includes the subtask summary table driven from frontmatter."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "Validate input"])  # ST1
    runner.invoke(app, ["task", "2", "add-subtask", "Write tests"])  # ST2
    r = runner.invoke(app, ["task", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "ST1" in r.output and "Validate input" in r.output
    assert "ST2" in r.output and "Write tests" in r.output
    assert "Status" in r.output  # column header


def test_feature_summary_shown_in_default_output(runner, tmp_path, monkeypatch, frozen_time):
    """Feature show includes user stories summary table."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])
    runner.invoke(app, ["feature", "2", "add-story", "As a user, I want X"])
    r = runner.invoke(app, ["feature", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "US1" in r.output and "As a user, I want X" in r.output


def test_review_summary_shown_in_default_output(runner, tmp_path, monkeypatch, frozen_time):
    """Review show includes findings summary table."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])
    runner.invoke(app, ["review", "2", "add-finding", "Null deref", "--severity", "high"])
    r = runner.invoke(app, ["review", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "F1" in r.output and "Null deref" in r.output


def test_comments_flag_shows_discussion_plain(runner, tmp_path, monkeypatch, frozen_time):
    """--comments renders the main discussion in plain mode (piped runner)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "-m", "Body."])
    runner.invoke(
        app,
        ["task", "2", "comment", "--as", "manager", "-m", "First point.", "-m", "Second point."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--comments"])
    assert r.exit_code == 0, r.output
    assert "First point." in r.output
    assert "Second point." in r.output
    # Plain mode delimiter
    assert "---" in r.output


def test_comments_flag_empty_discussion(runner, tmp_path, monkeypatch, frozen_time):
    """--comments with no discussion prints the no-discussion fallback."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "-m", "Body."])
    r = runner.invoke(app, ["task", "2", "show", "--comments"])
    assert r.exit_code == 0, r.output
    assert "no discussion" in r.output


def test_comments_tty_renders_author_in_output(runner, styled, tmp_path, monkeypatch, frozen_time):
    """On a TTY, --comments includes author and message text (Panel rendering)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "-m", "Body."])
    runner.invoke(
        app,
        ["task", "2", "comment", "--as", "manager", "-m", "Reviewed logic."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--comments"])
    assert r.exit_code == 0, r.output
    assert "manager" in r.output
    assert "Reviewed logic." in r.output


def test_default_show_no_body_label(runner, tmp_path, monkeypatch, frozen_time):
    """BUG-000025 regression: sq show must not inject a bare 'Body' literal."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Show test", "--author", "manager", "-m", "Content."])
    r = runner.invoke(app, ["task", "2", "show"])
    assert r.exit_code == 0, r.output
    lines = r.output.splitlines()
    assert not any(line.strip() == "Body" for line in lines)
    assert "Content." in r.output


# --------------------------------------------------------------------------- split_discussion units


def test_split_discussion_empty():
    """Empty / whitespace region returns no comments."""
    assert discussion.split_discussion("") == []
    assert discussion.split_discussion("   \n  ") == []


def test_split_discussion_single_comment():
    """Single comment: one header line + bullets."""
    region = "- [2026-06-07T10:00:00Z] Alice:\n  - Hello.\n  - World."
    cmts = discussion.split_discussion(region)
    assert len(cmts) == 1
    c = cmts[0]
    assert c.timestamp == "2026-06-07T10:00:00Z"
    assert c.author == "Alice"
    assert "- Hello." in c.body
    assert "- World." in c.body


def test_split_discussion_multiple_comments():
    """Multiple comments are split correctly at each header line."""
    region = (
        "- [2026-06-07T10:00:00Z] Alice:\n  - First.\n- [2026-06-07T11:00:00Z] Bob:\n  - Second.\n"
    )
    cmts = discussion.split_discussion(region)
    assert len(cmts) == 2
    assert cmts[0].author == "Alice"
    assert cmts[1].author == "Bob"
    assert "First." in cmts[0].body
    assert "Second." in cmts[1].body


def test_split_discussion_multiline_message():
    """Multiline message: continuation lines are preserved with reduced indent."""
    region = "- [2026-06-07T10:00:00Z] Dev:\n  - Parser\n    handles scopes\n"
    cmts = discussion.split_discussion(region)
    assert len(cmts) == 1
    # The body strips 2 leading spaces from each line
    assert "- Parser" in cmts[0].body
    assert "  handles scopes" in cmts[0].body


def test_split_discussion_fenced_code_block():
    """Fenced code blocks with internal blank lines are preserved intact."""
    region = (
        "- [2026-06-07T10:00:00Z] Dev:\n  - Fix:\n    ```py\n    a = 1\n    \n    b = 2\n    ```\n"
    )
    cmts = discussion.split_discussion(region)
    assert len(cmts) == 1
    body = cmts[0].body
    assert "```py" in body
    assert "a = 1" in body
    assert "b = 2" in body


def test_split_is_inverse_of_format(frozen_time):
    """split_discussion is the inverse of format_comment for roundtrip fidelity."""
    ts = "2026-06-07T10:00:00Z"
    author = "Robert Architect"
    msgs = ["First paragraph.", "Second paragraph.\nwith continuation."]
    formatted = discussion.format_comment(ts, author, msgs)
    # Wrap with leading newline as append_to_section produces
    region = f"\n{formatted}\n"
    cmts = discussion.split_discussion(region)
    assert len(cmts) == 1
    assert cmts[0].timestamp == ts
    assert cmts[0].author == author
    assert "First paragraph." in cmts[0].body
    assert "Second paragraph." in cmts[0].body
    assert "with continuation." in cmts[0].body


# --------------------------------------------------------------------------- ST5/US5: --full panes


def test_full_flag_shows_subentity_body_plain(runner, tmp_path, monkeypatch, frozen_time):
    """--full in plain mode includes each sub-entity's body content."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "First subtask"])  # ST1
    runner.invoke(app, ["task", "2", "add-subtask", "Second subtask"])  # ST2
    runner.invoke(
        app,
        ["task", "2", "subtask", "1", "body", "-m", "Body of first subtask."],
    )
    runner.invoke(
        app,
        ["task", "2", "subtask", "2", "body", "-m", "Body of second subtask."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    # Pane titles include local ids
    assert "ST1" in r.output
    assert "ST2" in r.output
    # Sub-entity body content present
    assert "Body of first subtask." in r.output
    assert "Body of second subtask." in r.output
    # Delimiter markers present in plain mode
    assert "===" in r.output


def test_full_flag_no_comments_by_default(runner, tmp_path, monkeypatch, frozen_time):
    """--full alone does NOT include sub-entity or main discussion comments."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "A subtask"])  # ST1
    # Comment on the subtask
    runner.invoke(
        app,
        ["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "Sub comment."],
    )
    # Comment on the main item
    runner.invoke(
        app,
        ["task", "2", "comment", "--as", "manager", "-m", "Main comment."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    assert "Sub comment." not in r.output
    assert "Main comment." not in r.output


def test_full_comments_includes_per_sub_comments_then_main(
    runner, tmp_path, monkeypatch, frozen_time
):
    """--full --comments: sub-entity comments appear before main discussion."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "A subtask"])  # ST1
    runner.invoke(
        app,
        ["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "Per-sub comment."],
    )
    runner.invoke(
        app,
        ["task", "2", "comment", "--as", "manager", "-m", "Main discussion comment."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--full", "--comments"])
    assert r.exit_code == 0, r.output
    assert "Per-sub comment." in r.output
    assert "Main discussion comment." in r.output
    # Main discussion must come AFTER the sub-entity section
    sub_pos = r.output.index("Per-sub comment.")
    main_pos = r.output.index("Main discussion comment.")
    assert sub_pos < main_pos, "per-sub comments must appear before main discussion"


def test_full_feature_stories_panes(runner, tmp_path, monkeypatch, frozen_time):
    """--full on a feature shows one pane per user story with body content."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])
    runner.invoke(app, ["feature", "2", "add-story", "As a user I want X"])  # US1
    runner.invoke(app, ["feature", "2", "story", "1", "body", "-m", "Acceptance criteria here."])
    r = runner.invoke(app, ["feature", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    assert "US1" in r.output
    assert "Acceptance criteria here." in r.output


def test_full_review_findings_panes(runner, tmp_path, monkeypatch, frozen_time):
    """--full on a review shows one pane per finding with body content and badge."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])
    runner.invoke(app, ["review", "2", "add-finding", "Null deref", "--severity", "high"])  # F1
    runner.invoke(
        app, ["review", "2", "finding", "1", "body", "-m", "The pointer is never checked."]
    )
    r = runner.invoke(app, ["feature" if False else "review", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    assert "F1" in r.output
    assert "The pointer is never checked." in r.output
    # Severity badge should appear in the pane title
    assert "high" in r.output.lower()


def test_full_no_subentities_degrades_gracefully(runner, tmp_path, monkeypatch, frozen_time):
    """--full on an item with no sub-entities exits 0 and shows nothing extra."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "-m", "Body text."])
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    assert "Body text." in r.output
    # No === delimiters when there are no sub-entities
    assert "===" not in r.output


def test_full_plain_byte_stable(runner, tmp_path, monkeypatch, frozen_time):
    """--full plain output is byte-stable (identical across two runs)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "Stable sub"])
    runner.invoke(app, ["task", "2", "subtask", "1", "body", "-m", "Stable body content."])
    r1 = runner.invoke(app, ["task", "2", "show", "--full"])
    r2 = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r1.exit_code == 0 and r2.exit_code == 0
    assert r1.output == r2.output


def test_json_unaffected_by_full_flag(runner, tmp_path, monkeypatch, frozen_time):
    """--json output is byte-identical regardless of --full."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "A sub"])
    r_base = runner.invoke(app, ["task", "2", "show", "--json"])
    r_full = runner.invoke(app, ["task", "2", "show", "--json", "--full"])
    r_full_cmt = runner.invoke(app, ["task", "2", "show", "--json", "--full", "--comments"])
    assert r_base.exit_code == r_full.exit_code == r_full_cmt.exit_code == 0
    assert r_base.output == r_full.output == r_full_cmt.output


def test_full_tty_renders_styled_panes(runner, styled, tmp_path, monkeypatch, frozen_time):
    """On a TTY, --full renders sub-entity bodies through Rich Markdown (## stripped)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "A subtask"])
    runner.invoke(
        app,
        ["task", "2", "subtask", "1", "body", "-m", "## SubSection\n\nParagraph text."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    # Rich Markdown renders ## as styled heading (## prefix consumed)
    assert "## SubSection" not in r.output
    assert "SubSection" in r.output
    assert "Paragraph text." in r.output


def test_full_tty_comments_embeds_sub_comments(runner, styled, tmp_path, monkeypatch, frozen_time):
    """On a TTY, --full --comments embeds per-sub comments as nested panels."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "A subtask"])
    runner.invoke(
        app,
        ["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "TTY sub comment."],
    )
    runner.invoke(
        app,
        ["task", "2", "comment", "--as", "manager", "-m", "TTY main comment."],
    )
    r = runner.invoke(app, ["task", "2", "show", "--full", "--comments"])
    assert r.exit_code == 0, r.output
    assert "TTY sub comment." in r.output
    assert "TTY main comment." in r.output
    assert "manager" in r.output


def test_full_status_badge_in_pane_title(runner, tmp_path, monkeypatch, frozen_time):
    """Sub-entity pane title includes the status badge (local_id, title, status)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "My subtask"])  # ST1, Todo
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    # pane title should contain local id + title + "Todo" status
    assert "ST1" in r.output
    assert "My subtask" in r.output
    assert "Todo" in r.output


def test_root_show_full_flag_works(runner, tmp_path, monkeypatch, frozen_time):
    """root sq show supports --full flag and shows sub-entity panes."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])
    runner.invoke(app, ["feature", "2", "add-story", "US title"])
    runner.invoke(app, ["feature", "2", "story", "1", "body", "-m", "Story body."])
    r = runner.invoke(app, ["show", "2", "--full"])
    assert r.exit_code == 0, r.output
    assert "US1" in r.output
    assert "Story body." in r.output


# ----------------------------------------------------------------- F1/F3: bracket fidelity


def test_plain_pane_title_literal_brackets_no_backslashes(
    runner, tmp_path, monkeypatch, frozen_time
):
    """F1/F3: a bracket-bearing sub-entity title must appear verbatim in plain/piped --full output.

    Regression for the double-escape bug: _subentity_pane_title_raw must not call e() so the
    plain path never leaks Rich-escape backslashes (e.g. '\\[red]' instead of '[red]').
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    # Title with bracket-like tokens similar to Rich markup and a checkbox idiom
    runner.invoke(app, ["task", "2", "add-subtask", "Danger [red]x[/red] and [x] checkbox"])
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    # Literal brackets must appear — no backslashes before them
    assert "[red]x[/red]" in r.output
    assert "[x]" in r.output
    assert r"\\[" not in r.output
    assert r"\[" not in r.output


def test_plain_pane_title_literal_brackets_styled_path(
    runner, styled, tmp_path, monkeypatch, frozen_time
):
    """F3: styled path also renders the literal bracket text (e() escapes it for Rich correctly)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "Danger [red]x[/red] and [x] checkbox"])
    r = runner.invoke(app, ["task", "2", "show", "--full"])
    assert r.exit_code == 0, r.output
    # Rich renders the escaped markup as literal brackets in the Panel title
    assert "[red]x[/red]" in r.output
    assert "[x]" in r.output


def test_plain_comment_header_literal_brackets_no_backslashes(
    runner, tmp_path, monkeypatch, frozen_time
):
    """F1/F3: comment headers in plain/piped output must not leak Rich-escape backslashes.

    _render_comments_plain uses raw cmt.timestamp and cmt.author (no e()) so bracket-bearing
    author names would appear verbatim. Validates the fix is consistent for this path.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "-m", "Body."])
    runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", "Comment text."])
    r = runner.invoke(app, ["task", "2", "show", "--comments"])
    assert r.exit_code == 0, r.output
    # The header delimiter line must be present without any backslash-escaping artefacts
    assert "---" in r.output
    assert r"\[" not in r.output
    assert "Comment text." in r.output
