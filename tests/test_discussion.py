from squads import _discussion as discussion
from squads import _sections as sections
from squads._models._subentity import SubEntity


def test_format_comment():
    out = discussion.format_comment("2026-06-07T10:00:00Z", "Robert Architect", ["a", "b"])
    assert out == "- [2026-06-07T10:00:00Z] Robert Architect:\n  - a\n  - b"


def test_format_comment_nests_multiline_messages():
    out = discussion.format_comment(
        "2026-06-07T10:00:00Z", "Olivia Lead", ["Parser\nhandles scopes", "@qa verify"]
    )
    assert out == (
        "- [2026-06-07T10:00:00Z] Olivia Lead:\n"
        "  - Parser\n"
        "    handles scopes\n"  # continuation line nests under its bullet
        "  - @qa verify"
    )


def test_format_comment_nests_a_fenced_code_block():
    out = discussion.format_comment(
        "2026-06-07T10:00:00Z", "Dev", ["Fix:\n```py\na = 1\n\nb = 2\n```"]
    )
    # fence, code, and the internal blank line all sit at the 4-space bullet content column
    assert out == (
        "- [2026-06-07T10:00:00Z] Dev:\n"
        "  - Fix:\n"
        "    ```py\n"
        "    a = 1\n"
        "    \n"  # blank line inside the block stays indented, not dropped to column 0
        "    b = 2\n"
        "    ```"
    )


def test_extract_mentions():
    text = "ping @qa and @reviewer, not email me@host or @ alone"
    assert discussion.extract_mentions(text) == {"qa", "reviewer"}


def _sub(local_id: str, **kw) -> SubEntity:
    return SubEntity(local_id=local_id, status=kw.pop("status", "Todo"), **kw)


def test_next_local_id():
    assert discussion.next_local_id([], "story") == "US1"
    assert discussion.next_local_id([_sub("US1"), _sub("US2")], "story") == "US3"
    assert discussion.next_local_id([_sub("ST5")], "subtask") == "ST6"


def test_build_block_uses_given_body():
    block = discussion.build_block("subtask", "ST1", "Validate", body="custom body text")
    assert "custom body text" in block
    assert discussion.body_placeholder("subtask") not in block
    # without an explicit body the placeholder is kept
    default = discussion.build_block("subtask", "ST1", "Validate")
    assert discussion.body_placeholder("subtask") in default


def test_build_block_has_no_meta_but_ships_head():
    # state lives in frontmatter now; the block only scaffolds prose + an (empty) :head region
    block = discussion.build_block("finding", "F1", "Null deref")
    assert ":meta" not in block
    assert "<!-- sq:finding:F1:head -->" in block
    assert "<!-- sq:finding:F1:body -->" in block
    assert "### F1 — Null deref" in block


def test_render_summary():
    subs = [
        SubEntity(
            local_id="F1",
            title="Null deref",
            status="Open",
            severity="high",
            assignee="qa",
        )
    ]
    out = discussion.render_summary("finding", subs)
    assert "| Finding | Severity | Status | Assignee | Title |" in out
    assert "🟠 high" in out and "Open" in out and "qa" in out
    assert discussion.render_summary("finding", []) == ""


def test_severity_badge_and_summary_degrade_gracefully_without_collection():
    """A spec that dropped/renamed the severity collection never crashes — the raw code plus
    the neutral fallback badge, mirroring _status_badge's graceful degradation."""
    from squads._workflow import bundled_spec

    spec = bundled_spec().model_copy(update={"collections": {}})
    coll = discussion.resolve_collection("finding", "severity", spec)
    assert discussion.badge_render(coll, "high", spec, as_label=True) == "⚪ High"

    subs = [SubEntity(local_id="F1", title="Null deref", status="Open", severity="high")]
    out = discussion.render_summary("finding", subs, spec)
    assert "⚪ high" in out  # emoji degrades; the raw code still renders, never crashes


def test_severity_badge_falls_back_for_an_undeclared_code():
    """A stored code that isn't (or is no longer) a badge in the collection also degrades
    gracefully rather than raising a KeyError (unlike the old SEVERITY_EMOJI[...] dict)."""
    assert discussion.badge_render("severity", "nonexistent", as_label=True) == "⚪ Nonexistent"


def test_set_head_renders_badges_into_empty_region():
    block = discussion.build_block("subtask", "ST1", "Validate")
    out = discussion.set_head(
        block,
        "subtask",
        "ST1",
        status="InProgress",
        assignee_name="Grace Hopper",
        story="US1 — Login",
    )
    head = sections.get_section(out, "subtask:ST1:head")
    assert head is not None
    assert "**Status:** 🟡 In Progress" in head
    assert "**Assignee:** Grace Hopper" in head
    assert "**Implements:** US1 — Login" in head
