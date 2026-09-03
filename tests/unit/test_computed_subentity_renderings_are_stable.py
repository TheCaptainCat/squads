"""The five computed renderings of sub-entity state never read the (now-retired) `:head`/
`:summary` body regions — they derive from the frontmatter model alone, unchanged by whether
those regions exist in the file at all.

Two kinds of proof: an in-memory one showing three of the renderings need no file (built off a
bare `SubEntity`/`SubentityDetail`, never written anywhere), and an end-to-end CLI one pinning
the exact bytes `sq show`/`sq <kind>s`/`--full`/`--raw`/`--json` produce for a `finding` carrying
a `severity` value — the shape that exercises a badge cell, not just plain text.
"""

import json

import pytest

from squads._cli._common import (
    _subentity_badge_line,
    _subentity_pane_title_raw,
    build_subentity_json,
)
from squads._models._subentity import SubEntity
from squads._services._results import SubentityDetail
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _finding() -> SubEntity:
    return SubEntity(
        local_id="F1", title="Null deref", status="Open", severity="critical", assignee="qa"
    )


def test_the_badge_line_and_pane_title_derive_from_a_bare_subentity_no_file_involved() -> None:
    sub = _finding()
    assert _subentity_badge_line(sub, "finding") == "🔴 Open  🔴 Critical  qa"
    assert _subentity_pane_title_raw(sub, "finding") == (
        "F1 — Null deref  🔴 Open  🔴 Critical  qa"
    )


def test_the_json_payload_derives_from_a_bare_subentity_detail_no_file_involved() -> None:
    spec = bundled_spec()
    detail = SubentityDetail(info=_finding(), body="Body text.", discussion="")
    payload = build_subentity_json(spec, "finding", detail)
    assert payload["local_id"] == "F1"
    assert payload["severity"] == "critical"
    assert payload["assignee"] == "qa"
    assert payload["body"] == "Body text."
    assert payload["badges"] == {"severity": "critical"}
    assert payload["discussion"] == []


async def test_show_full_raw_json_and_list_table_pin_exact_bytes_for_a_severity_finding(
    project, invoke
) -> None:
    await invoke(["dev", "add", "--tech", "python", "--name", "Grace Hopper"])
    await invoke(["create", "review", "R", "--author", "manager"])
    await invoke(["review", "3", "add-finding", "Null deref", "--severity", "critical"])
    await invoke(["review", "3", "finding", "1", "update", "--assignee", "python-dev"])
    await invoke(["review", "3", "finding", "1", "body", "-m", "Body of finding."])

    show = await invoke(["review", "3", "show"])
    assert show.output == (
        "╭───────────────────────────────╮\n"
        "│ REV-3  (review)               │\n"
        "│ title: R                      │\n"
        "│ status: Requested             │\n"
        "│ author: manager               │\n"
        "│ file: reviews/REV-000003-r.md │\n"
        "╰───────────────────────────────╯\n"
        "\n"
        "## Scope\n"
        "\n"
        "_TODO: what is under review?_\n"
        "\n"
        "Finding  Severity     Status  Assignee    Title     \n"
        "F1       🔴 critical  Open    python-dev  Null deref\n"
    )

    full = await invoke(["review", "3", "show", "--full"])
    assert full.output == show.output + (
        "=== F1 — Null deref  🔴 Open  🔴 Critical  python-dev ===\nBody of finding.\n\n"
    )

    raw = await invoke(["review", "3", "show", "--raw", "--full"])
    assert raw.output == (
        "# REV-3 — R\n"
        "\n"
        "- **status:** Requested\n"
        "- **author:** manager\n"
        "\n"
        "## Scope\n"
        "\n"
        "_TODO: what is under review?_\n"
        "\n"
        "## Finding F1 — Null deref\n"
        "\n"
        "🔴 Open  🔴 Critical  python-dev\n"
        "\n"
        "Body of finding.\n"
    )

    tbl = await invoke(["review", "3", "findings"])
    assert tbl.output == (
        "Finding  Severity     Status  Assignee    Title     \n"
        "F1       🔴 critical  Open    python-dev  Null deref\n"
    )

    js = await invoke(["review", "3", "show", "--json"])
    payload = json.loads(js.output)
    (sub,) = payload["subentities"]
    assert sub["local_id"] == "F1"
    assert sub["severity"] == "critical"
    assert sub["assignee"] == "python-dev"
    assert sub["body"] == "Body of finding."
    assert sub["badges"] == {"severity": "critical"}
