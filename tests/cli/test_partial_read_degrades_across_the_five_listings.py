"""Table-driven coverage of the partial-read contract (exit code 4, and one compact
``{"omitted": [...]}`` line on stderr under ``--json``) across the five bound commands:
``inbox``, ``search``, ``board list``, ``memory list``, ``memory search``.

Each command is driven through four shapes -- nothing unreadable, some unreadable, everything
unreadable, and a listing that is genuinely empty (nothing to list, nothing unreadable) -- and
each shape is asserted separately on stdout, the exit code, and stderr: the three faces the
contract has, so a payload change or a stream leak cannot slip through by collapsing them into
one assertion. Exit codes are read straight off ``invoke()``'s captured result, never through a
shell pipe (which would report its own status, not the command's).

Also covers the edges the per-command tables cannot: precedence (a prior ``SquadsError``
outranks a partial read), the class boundary (``check``/``repair``/``migrate up`` stay on
their own, pre-existing exit codes), and the one-line-of-stderr-that-parses-as-JSON consumer
rule holding even with a prose co-tenant (the ``sq sync`` version notice) on the same stream.
"""

import json
from typing import cast

import pytest

from _helpers import create_item, make_unreadable_by_the_os
from squads._index._resolver import item_file
from squads._memory._store import role_folder
from squads._models._schema import SCHEMA_VERSION

pytestmark = pytest.mark.anyio

_SHAPES = ("nothing_unreadable", "some_unreadable", "all_unreadable", "empty_ordinary")

#: The omissions report's shape: one `omitted` key, a list of flat `{code, source, message}`
#: string-valued objects.
type OmissionsReport = dict[str, list[dict[str, str]]]


def _omissions_report(stderr: str) -> OmissionsReport:
    """The one line of *stderr* that parses as a JSON object -- the consumer rule the
    omissions report is found by. Fails loudly if that is not exactly one line, so a stray
    second JSON-shaped line (or none at all) is a test failure, not a silent pass."""
    hits: list[dict[str, object]] = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            hits.append(parsed)
    assert len(hits) == 1, f"expected exactly one JSON-object line on stderr, got:\n{stderr!r}"
    return cast(OmissionsReport, hits[0])


def _assert_clean(result, jresult, *, ids_in_payload: list[str]) -> None:
    assert result.exit_code == 0, result.output
    assert result.stderr == "", result.stderr
    assert jresult.exit_code == 0, jresult.output
    assert jresult.stderr == "", jresult.stderr
    payload = json.loads(jresult.stdout)
    assert isinstance(payload, list)
    assert [row.get("id") or row.get("slug") for row in payload] == ids_in_payload


def _assert_degraded(
    result, jresult, *, ids_in_payload: list[str], omitted_count: int
) -> OmissionsReport:
    assert result.exit_code == 4, result.output
    assert jresult.exit_code == 4, jresult.output
    payload = json.loads(jresult.stdout)
    assert isinstance(payload, list)
    assert [row.get("id") or row.get("slug") for row in payload] == ids_in_payload
    report = _omissions_report(jresult.stderr)
    assert list(report.keys()) == ["omitted"]
    assert len(report["omitted"]) == omitted_count
    for entry in report["omitted"]:
        assert entry["code"] == "unreadable"
        assert entry["source"]
        assert entry["message"]
    # Human mode: one `error:` line per omission, on stderr only -- never leaking onto stdout.
    assert "error:" not in result.stdout
    assert result.stderr.count("error:") == omitted_count, result.stderr
    return report


# --------------------------------------------------------------------------- inbox / search


@pytest.mark.parametrize("command", ["inbox", "search"])
@pytest.mark.parametrize("shape", _SHAPES)
async def test_inbox_and_search_across_degraded_read_shapes(svc, invoke, command, shape):
    def args(json_out: bool) -> list[str]:
        base = ["inbox", "manager"] if command == "inbox" else ["search", "quinoa"]
        return [*base, "--json"] if json_out else base

    if shape == "empty_ordinary":
        result = await invoke(args(False))
        jresult = await invoke(args(True))
        _assert_clean(result, jresult, ids_in_payload=[])
        return

    if shape == "nothing_unreadable":
        good = (await create_item(svc, "task", "readable")).item
        await svc.set_body(good.id, "the quinoa line, and @manager is called out")
        result = await invoke(args(False))
        jresult = await invoke(args(True))
        _assert_clean(result, jresult, ids_in_payload=[good.id])
        assert good.id in result.stdout
        return

    if shape == "some_unreadable":
        good = (await create_item(svc, "task", "readable")).item
        await svc.set_body(good.id, "the quinoa line, and @manager is called out")
        bad = (await create_item(svc, "task", "unreadable")).item
        await svc.set_body(bad.id, "also quinoa, also @manager")
        make_unreadable_by_the_os(item_file(svc.paths, bad))
        result = await invoke(args(False))
        jresult = await invoke(args(True))
        report = _assert_degraded(result, jresult, ids_in_payload=[good.id], omitted_count=1)
        assert good.id in result.stdout
        assert report["omitted"][0]["source"] == bad.id
        return

    # all_unreadable: the only item in the corpus is the broken one -- no separate readable
    # item this time, or this would silently be the some_unreadable shape in disguise.
    only = (await create_item(svc, "task", "unreadable")).item
    await svc.set_body(only.id, "also quinoa, also @manager")
    make_unreadable_by_the_os(item_file(svc.paths, only))
    result = await invoke(args(False))
    jresult = await invoke(args(True))
    report = _assert_degraded(result, jresult, ids_in_payload=[], omitted_count=1)
    assert report["omitted"][0]["source"] == only.id


# --------------------------------------------------------------------------- board list


@pytest.mark.parametrize("shape", _SHAPES)
async def test_board_list_across_degraded_read_shapes(project, svc, invoke, shape):
    if shape == "empty_ordinary":
        result = await invoke(["board", "list"])
        jresult = await invoke(["board", "list", "--json"])
        _assert_clean(result, jresult, ids_in_payload=[])
        return

    good = await svc.board_post("op-alice", "a fine notice")

    if shape == "nothing_unreadable":
        result = await invoke(["board", "list"])
        jresult = await invoke(["board", "list", "--json"])
        _assert_clean(result, jresult, ids_in_payload=[good.id])
        assert "a fine notice" in result.output
        return

    if shape == "some_unreadable":
        bad = await svc.board_post("op-alice", "a corrupt notice")
        bad_path = project.squad_dir / "board" / f"{bad.id}.md"
        make_unreadable_by_the_os(bad_path)
        result = await invoke(["board", "list"])
        jresult = await invoke(["board", "list", "--json"])
        report = _assert_degraded(result, jresult, ids_in_payload=[good.id], omitted_count=1)
        assert str(bad_path.relative_to(project.squad_dir)) == report["omitted"][0]["source"]
        return

    # all_unreadable: the only notice is the broken one -- `good` above stands in as the
    # notice to corrupt instead (no separate readable one this time).
    only_path = project.squad_dir / "board" / f"{good.id}.md"
    make_unreadable_by_the_os(only_path)
    result = await invoke(["board", "list"])
    jresult = await invoke(["board", "list", "--json"])
    report = _assert_degraded(result, jresult, ids_in_payload=[], omitted_count=1)
    assert str(only_path.relative_to(project.squad_dir)) == report["omitted"][0]["source"]


# --------------------------------------------------------------------------- memory list / search


@pytest.mark.parametrize("command", ["list", "search"])
@pytest.mark.parametrize("shape", _SHAPES)
async def test_memory_list_and_search_across_degraded_read_shapes(
    project, svc, invoke, command, shape
):
    def args(json_out: bool) -> list[str]:
        base = ["memory", "manager", command] + (["xylophone"] if command == "search" else [])
        return [*base, "--json"] if json_out else base

    if shape == "empty_ordinary":
        result = await invoke(args(False))
        jresult = await invoke(args(True))
        _assert_clean(result, jresult, ids_in_payload=[])
        return

    good = await svc.memory_add("manager", "a fine searchable fact xylophone", slug="good")

    if shape == "nothing_unreadable":
        result = await invoke(args(False))
        jresult = await invoke(args(True))
        _assert_clean(result, jresult, ids_in_payload=[good.slug])
        assert good.slug in result.stdout
        return

    if shape == "some_unreadable":
        bad = await svc.memory_add("manager", "a corrupt searchable fact xylophone", slug="bad")
        bad_path = role_folder(project, "manager") / f"{bad.slug}.md"
        make_unreadable_by_the_os(bad_path)
        result = await invoke(args(False))
        jresult = await invoke(args(True))
        report = _assert_degraded(result, jresult, ids_in_payload=[good.slug], omitted_count=1)
        assert str(bad_path.relative_to(project.squad_dir)) == report["omitted"][0]["source"]
        return

    only_path = role_folder(project, "manager") / f"{good.slug}.md"
    make_unreadable_by_the_os(only_path)
    result = await invoke(args(False))
    jresult = await invoke(args(True))
    report = _assert_degraded(result, jresult, ids_in_payload=[], omitted_count=1)
    assert str(only_path.relative_to(project.squad_dir)) == report["omitted"][0]["source"]


# --------------------------------------------------------------------------- precedence


async def test_a_prior_squads_error_outranks_a_partial_read(svc, invoke):
    """1/2/3 outrank 4: an unresolvable role fails before the corpus walk that would
    otherwise flag the unreadable file ever runs -- so the exit code stays 1, not 4."""
    bad = (await create_item(svc, "task", "unreadable")).item
    await svc.set_body(bad.id, "@manager mentioned")
    make_unreadable_by_the_os(item_file(svc.paths, bad))

    result = await invoke(["inbox", "no-such-role-at-all"])

    assert result.exit_code == 1, result.output


# --------------------------------------------------------------------------- class boundary


async def test_check_and_repair_stay_outside_the_partial_read_class(svc, invoke):
    """`sq check`/`sq repair` keep their own, pre-existing exit codes on a degraded read --
    the class is explicitly bound to a five-command list, not to "anything that walks the
    corpus"."""
    bad = (await create_item(svc, "task", "unreadable")).item
    make_unreadable_by_the_os(item_file(svc.paths, bad))

    check_result = await invoke(["check"])
    assert check_result.exit_code == 3, check_result.output

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code == 1, repair_result.output


async def test_migrate_up_stays_outside_the_partial_read_class(svc, invoke):
    """Same boundary, for `sq migrate up`: a degraded read elsewhere in the corpus must not
    borrow the new code -- checked here on the (normal) already-current-schema path, which
    returns before ever touching the corrupt file."""
    bad = (await create_item(svc, "task", "unreadable")).item
    make_unreadable_by_the_os(item_file(svc.paths, bad))

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "already at schema" in result.output


# --------------------------------------------------------------------------- one JSON line


async def test_the_omissions_report_is_the_one_json_line_with_a_prose_cotenant(svc, invoke):
    """The `sq sync` version notice is a real prose co-tenant on stderr under `--json` --
    the consumer rule ("the one line of stderr that parses as a JSON object is the report")
    has to hold with that line present, not only on an otherwise-quiet stderr."""
    bad = (await create_item(svc, "task", "unreadable")).item
    await svc.set_body(bad.id, "@manager mentioned, quinoa too")
    make_unreadable_by_the_os(item_file(svc.paths, bad))
    (svc.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        f'schema_version = "{SCHEMA_VERSION}"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        'squads_version = "0.0.1"\n',
        encoding="utf-8",
    )

    result = await invoke(["inbox", "manager", "--json"])

    assert result.exit_code == 4, result.output
    stderr_lines = [ln for ln in result.stderr.splitlines() if ln.strip()]
    assert any("sq sync" in ln for ln in stderr_lines), "the version notice must still fire"
    report = _omissions_report(result.stderr)
    assert list(report.keys()) == ["omitted"]
    assert report["omitted"][0]["source"] == bad.id
