"""Every function under ``src/squads/_cli`` that consumes a repair-corridor result must be one
of a fully-enumerated set of known sites, each classified as reporting every channel, reporting
neither (a defect), or not actually a reporting site. Sites are found by walking the parsed
source, not a hand-picked command list, so a future unclassified consumer fails outright."""

import ast
from pathlib import Path

# --------------------------------------------------------------------------- discovery

#: Attribute names that shape a read off a repair-corridor result value, plus the producer
#: method names that return one of these result types in the first place — closing the gap a
#: channel-only filter cannot see: a consumer that calls a producer and reads nothing off the
#: result is still a consumer, and is exactly the defect this module exists to catch.
_TARGET_ATTRS = frozenset(
    {
        "repair",
        "skipped",
        "unreadable",
        "strip_notice",
        "sync",
        "run_pending_migrations",
    }
)

#: Bare-name (not attribute-style) producer calls: ``adopt`` is imported directly rather than
#: reached through a ``svc.`` attribute, so an attribute-only filter cannot see it at all.
_BARE_NAME_TARGETS = frozenset({"svc_adopt"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cli_root() -> Path:
    return _repo_root() / "src" / "squads" / "_cli"


def _sites_in_module(source: str, rel: str) -> set[tuple[str, str]]:
    """Every ``(module-relative-posix-path, enclosing function's qualified name)`` in *source*
    containing a target attribute read or a bare-name producer call."""
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError:
        return set()
    sites: set[tuple[str, str]] = set()
    _collect(tree, rel, [], sites)
    return sites


def _collect(node: ast.AST, rel: str, stack: list[str], sites: set[tuple[str, str]]) -> None:
    for child in ast.iter_child_nodes(node):
        child_stack = stack
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            child_stack = [*stack, child.name]
        is_target_attr = isinstance(child, ast.Attribute) and child.attr in _TARGET_ATTRS
        is_bare_name_call = (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id in _BARE_NAME_TARGETS
        )
        if is_target_attr or is_bare_name_call:
            qualname = ".".join(child_stack) if child_stack else "<module>"
            sites.add((rel, qualname))
        _collect(child, rel, child_stack, sites)


def _consumer_sites(cli_root: Path) -> set[tuple[str, str]]:
    sites: set[tuple[str, str]] = set()
    for path in sorted(cli_root.rglob("*.py")):
        rel = path.relative_to(cli_root.parent.parent).as_posix()
        sites |= _sites_in_module(path.read_text(encoding="utf-8"), rel)
    return sites


def test_the_ast_scan_finds_a_read_a_raw_substring_grep_would_miss() -> None:
    """An AST walk finds a dotted attribute access wrapped across a line break, which a raw
    substring grep would miss."""
    adversarial = "def h() -> None:\n    x = (result\n        .skipped)\n"
    assert "result.skipped" not in adversarial, (
        "fixture no longer demonstrates a raw substring false zero"
    )

    found = _sites_in_module(adversarial, "adversarial.py")
    assert found == {("adversarial.py", "h")}, (
        "the AST-based scan must find an attribute read a raw substring grep misses"
    )


def test_a_newly_added_consumer_site_is_discovered_without_being_told_where_to_look() -> None:
    """A consumer this module has never seen, in a file it was never pointed at, still turns up."""
    synthetic = (
        "async def a_brand_new_command() -> None:\n"
        "    result = await svc.some_sweep()\n"
        "    for msg in result.unreadable:\n"
        "        console.print(msg)\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_brand_new_command")}


#: The three realistic consumer shapes a channel-only filter misses.
def test_a_sync_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """``svc.sync()`` consumed and never read is still discovered, via the producer name."""
    synthetic = (
        "async def a_quiet_sync_wrapper() -> None:\n"
        "    svc = get_service()\n"
        "    await svc.sync()\n"
        "    console.print('done')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_sync_wrapper")}


def test_a_run_pending_migrations_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """The same discovery holds for a ``svc.run_pending_migrations()`` call read nothing off."""
    synthetic = (
        "async def a_quiet_migration_wrapper() -> None:\n"
        "    svc = get_service()\n"
        "    await svc.run_pending_migrations()\n"
        "    console.print('done')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_migration_wrapper")}


def test_a_bare_name_svc_adopt_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """A bare-name ``svc_adopt(...)`` call read nothing off is still discovered."""
    synthetic = (
        "async def a_quiet_adopt_wrapper() -> None:\n"
        "    await svc_adopt(squad_dir='squads')\n"
        "    console.print('adopted')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_adopt_wrapper")}


# --------------------------------------------------------------------------- classification

#: (relative path, enclosing function) -> (classification, reason). Exactly the sites this
#: codebase has today under ``_cli/`` — a mismatch below is the whole point: this dict is a
#: completeness claim, not a convenience cache.
CLASSIFICATIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("squads/_cli/_main.py", "repair"): (
        "reports-every-channel",
        "the reference implementation — prints unreadable and skipped at error level and "
        "exits 1 when either is non-empty",
    ),
    ("squads/_cli/_migrate.py", "migrate_up"): (
        "reports-every-channel",
        "runs the same rebuild as its trailing step and reports both channels in repair's own "
        "wording, exiting 1 on either",
    ),
    ("squads/_cli/_main.py", "sync"): (
        "reports-every-channel",
        "consumes SyncSkips — the deduplicated skip/notice message list sync's own narrower "
        "sweep produces, printed in full — 'every channel' here means the complete channel "
        "set this result type exposes, which is the single one sync prints",
    ),
    ("squads/_cli/_main.py", "adopt"): (
        "reports-every-channel",
        "reads AdoptResult.repair and prints unreadable and skipped in repair's own wording, "
        "exiting 1 on either, matching sq repair on the identical corpus",
    ),
    ("squads/_cli/_main.py", "renumber"): (
        "not-a-reporting-site",
        "matches the discovery pattern only because it calls RenumberResult.strip_notice() — "
        "a method name shared with RepairResult, not the same type. RenumberResult carries no "
        "skipped/unreadable field at all; its own 'stripped' channel is a distinct, "
        "already-covered concern (test_repair_corridor_message_and_exit_parity's strip_notice "
        "coverage), not one this enumeration is about",
    ),
}

_VALID_CLASSIFICATIONS = frozenset(
    {"reports-every-channel", "reports-neither-channel", "not-a-reporting-site"}
)


def test_every_classification_label_is_one_of_the_three_known_shapes() -> None:
    """A typo'd classification label in the table above is caught before the check below."""
    for site, (label, _reason) in CLASSIFICATIONS.items():
        assert label in _VALID_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_no_site_is_classified_reports_neither_channel() -> None:
    """``reports-neither-channel`` names a defect; nothing in the table should ever carry it."""
    offenders = [
        site for site, (label, _r) in CLASSIFICATIONS.items() if label == "reports-neither-channel"
    ]
    assert not offenders, f"consumer site(s) reporting neither channel: {offenders}"


def test_the_discovered_sites_are_exactly_the_classified_five() -> None:
    discovered = _consumer_sites(_cli_root())
    expected = set(CLASSIFICATIONS)

    missing = expected - discovered
    assert not missing, (
        f"expected consumer site(s) no longer found (renamed or removed?): {missing}"
    )

    extra = discovered - expected
    assert not extra, (
        f"unclassified repair-corridor consumer site(s) found — classify each in "
        f"CLASSIFICATIONS above: {extra}"
    )
