from squads import discussion


def test_format_comment():
    out = discussion.format_comment("2026-06-07T10:00:00Z", "Robert Architect", ["a", "b"])
    assert out == "- [2026-06-07T10:00:00Z] Robert Architect:\n  - a\n  - b"


def test_extract_mentions():
    text = "ping @qa and @reviewer, not email me@host or @ alone"
    assert discussion.extract_mentions(text) == {"qa", "reviewer"}


def test_next_local_id():
    assert discussion.next_local_id("", "story") == "US1"
    text = "<!-- sq:story:US1 --><!-- sq:story:US2 -->"
    assert discussion.next_local_id(text, "story") == "US3"
    assert discussion.next_local_id("<!-- sq:subtask:ST5 -->", "subtask") == "ST6"


def test_list_blocks():
    block = discussion.build_story_block("US1", "As an admin, I want X")
    assert ("US1", "As an admin, I want X") in discussion.list_blocks(block, "story")
