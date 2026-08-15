"""`sq inbox`'s human render must never print an item with nothing under it.

The service-level suite proves the hit carries lines; this proves the operator sees them. The
`--desc` case is the one that mattered: the terminal showed the item and a blank, with no
indication of what had called the reader out, while `sq search` found the same text -- so the two
surfaces are asserted against each other here too, at the CLI, since that disagreement is what an
operator actually reported.
"""

import json

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("title", "description", "expected_line"),
    [
        ("@manager fix the parser", "", "@manager fix the parser"),
        ("a clean title", "ping @manager about this", "ping @manager about this"),
    ],
    ids=["mention_in_title", "mention_in_description"],
)
async def test_inbox_prints_the_authored_line_for_a_frontmatter_only_mention(
    invoke, svc, title, description, expected_line
):
    item = (await create_item(svc, "task", title, description=description)).item

    result = await invoke(["inbox", "manager"])

    assert result.exit_code == 0, result.output
    assert item.id in result.output
    assert expected_line in result.output


async def test_inbox_json_never_emits_a_hit_with_no_lines(invoke, svc):
    """The `--json` half: a consumer that renders per line got an entry with nothing to render.
    Asserted as an invariant over every hit rather than by indexing the one expected entry."""
    await create_item(svc, "task", "a clean title", description="ping @manager about this")
    await create_item(svc, "task", "@manager and one in a title")

    result = await invoke(["inbox", "manager", "--json"])

    assert result.exit_code == 0, result.output
    hits = json.loads(result.output)
    assert len(hits) == 2
    for hit in hits:
        assert len(hit["lines"]) == len(hit["regions"]) > 0, hit


async def test_inbox_and_search_report_the_same_item_for_the_same_authored_text(invoke, svc):
    item = (await create_item(svc, "task", "a clean title", description="ping @manager here")).item

    inbox = await invoke(["inbox", "manager"])
    search = await invoke(["search", "@manager"])

    assert item.id in inbox.output
    assert item.id in search.output
