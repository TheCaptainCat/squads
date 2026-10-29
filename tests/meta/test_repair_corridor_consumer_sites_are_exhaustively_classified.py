"""Every function under ``src/squads/_cli`` or in an operation handler (``_services/*_ops.py``)
that consumes a repair-corridor result is a classified site, and reads the channels it is
classified for. Sites are found by walking the parsed source, so a new consumer fails outright."""

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
_BARE_NAME_TARGETS = frozenset({"adopt"})

type Site = tuple[str, str]


def _src_root() -> Path:
    return Path(__file__).resolve().parents[2] / "src"


def _scanned_modules(src: Path) -> list[Path]:
    """The command modules and the operation handlers, which call the producers and map their
    results onto the DTOs the commands print."""
    squads = src / "squads"
    return sorted([*(squads / "_cli").rglob("*.py"), *(squads / "_services").glob("*_ops.py")])


def _reads_in_module(source: str, rel: str) -> dict[Site, set[str]]:
    """Every ``(module-relative-posix-path, enclosing function's qualified name)`` in *source*
    containing a target attribute read or a bare-name producer call, with the targets it reads."""
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError:
        return {}
    reads: dict[Site, set[str]] = {}
    _collect(tree, rel, [], reads)
    return reads


def _sites_in_module(source: str, rel: str) -> set[Site]:
    return set(_reads_in_module(source, rel))


def _collect(node: ast.AST, rel: str, stack: list[str], reads: dict[Site, set[str]]) -> None:
    for child in ast.iter_child_nodes(node):
        child_stack = stack
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            child_stack = [*stack, child.name]
        name = None
        if isinstance(child, ast.Attribute) and child.attr in _TARGET_ATTRS:
            name = child.attr
        elif (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id in _BARE_NAME_TARGETS
        ):
            name = child.func.id
        if name is not None:
            qualname = ".".join(child_stack) if child_stack else "<module>"
            reads.setdefault((rel, qualname), set()).add(name)
        _collect(child, rel, child_stack, reads)


def _consumer_reads(src: Path) -> dict[Site, set[str]]:
    reads: dict[Site, set[str]] = {}
    for path in _scanned_modules(src):
        rel = path.relative_to(src).as_posix()
        reads |= _reads_in_module(path.read_text(encoding="utf-8"), rel)
    return reads


def test_the_ast_scan_finds_a_read_a_raw_substring_grep_would_miss() -> None:
    """An AST walk finds a dotted attribute access wrapped across a line break."""
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


def test_a_bare_name_adopt_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """A bare-name ``adopt(...)`` call read nothing off is still discovered."""
    synthetic = (
        "async def a_quiet_adopt_wrapper() -> None:\n"
        "    await adopt(squad_dir='squads')\n"
        "    console.print('adopted')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_adopt_wrapper")}


# --------------------------------------------------------------------------- classification

#: (relative path, enclosing function) -> (classification, the names it must read, reason).
#: Exactly the sites this codebase has today under ``_cli/`` and the operation handlers — a
#: mismatch below is the whole point: this dict is a completeness claim, not a convenience cache.
#: A handler that calls a producer must read each channel off the result, so a report that
#: leaves one empty fails here rather than printing nothing.
CLASSIFICATIONS: dict[Site, tuple[str, frozenset[str], str]] = {
    ("squads/_services/_corpus_ops.py", "repair_squad"): (
        "reports-every-channel",
        frozenset({"repair", "unreadable"}),
        "maps the rebuild's unreadable files onto the report",
    ),
    ("squads/_services/_corpus_ops.py", "renumber_squad"): (
        "not-a-reporting-site",
        frozenset({"strip_notice"}),
        "matches only because it calls RenumberResult.strip_notice(), a method name shared with "
        "RepairResult; RenumberResult carries no skipped or unreadable field",
    ),
    ("squads/_services/_corpus_ops.py", "migrate_squad"): (
        "reports-every-channel",
        frozenset({"run_pending_migrations", "skipped", "repair", "unreadable"}),
        "maps each migration's skipped items and the trailing rebuild's unreadable files onto the "
        "report",
    ),
    ("squads/_services/_creation_ops.py", "adopt_squad"): (
        "reports-every-channel",
        frozenset({"adopt", "repair", "unreadable"}),
        "maps the import sweep's unreadable files onto the report",
    ),
    ("squads/_services/_squad_ops.py", "sync_squad"): (
        "reports-every-channel",
        frozenset({"sync"}),
        "puts the whole skip list sync returns, its one channel, on the report",
    ),
    ("squads/_cli/_main.py", "repair"): (
        "reports-every-channel",
        frozenset({"unreadable"}),
        "renders the report, then exits 1 when it names an unreadable file or refs left to check",
    ),
    ("squads/_cli/_render/_squad.py", "render_repair"): (
        "reports-every-channel",
        frozenset({"unreadable"}),
        "prints each unreadable file at error level, with the content notice and the missing ids",
    ),
    ("squads/_cli/_migrate.py", "migrate_up"): (
        "reports-every-channel",
        frozenset({"unreadable"}),
        "renders the report of the same rebuild as its trailing step, exiting 1 on an unreadable "
        "file as repair does",
    ),
    ("squads/_cli/_render/_squad.py", "render_migration"): (
        "reports-every-channel",
        frozenset({"skipped", "unreadable"}),
        "prints each migration's skipped items and the rebuild's unreadable files in repair's own "
        "wording",
    ),
    ("squads/_cli/_render/_check.py", "render_sync"): (
        "reports-every-channel",
        frozenset({"skipped"}),
        "consumes SyncReport.skipped — the deduplicated skip/notice message list sync's own "
        "narrower sweep produces, printed in full — 'every channel' here means the complete "
        "channel set this result type exposes, which is the single one sync prints",
    ),
    ("squads/_cli/_main.py", "adopt"): (
        "reports-every-channel",
        frozenset({"unreadable"}),
        "renders the report of the import sweep, exiting 1 on an unreadable file, matching sq "
        "repair on the identical corpus",
    ),
    ("squads/_cli/_render/_squad.py", "render_adopt"): (
        "reports-every-channel",
        frozenset({"unreadable"}),
        "prints the import sweep's unreadable files in repair's own wording",
    ),
}

_VALID_CLASSIFICATIONS = frozenset(
    {"reports-every-channel", "reports-neither-channel", "not-a-reporting-site"}
)


def test_every_classification_label_is_one_of_the_three_known_shapes() -> None:
    """A typo'd classification label in the table above is caught before the check below."""
    for site, (label, _reads, _reason) in CLASSIFICATIONS.items():
        assert label in _VALID_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_no_site_is_classified_reports_neither_channel() -> None:
    """``reports-neither-channel`` names a defect; nothing in the table should ever carry it."""
    offenders = [
        site
        for site, (label, _reads, _reason) in CLASSIFICATIONS.items()
        if label == "reports-neither-channel"
    ]
    assert not offenders, f"consumer site(s) reporting neither channel: {offenders}"


def test_the_discovered_sites_are_exactly_the_classified_ones() -> None:
    discovered = set(_consumer_reads(_src_root()))
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


def test_every_site_reads_the_channels_it_is_classified_for() -> None:
    reads = _consumer_reads(_src_root())
    short = {
        site: sorted(needed - reads.get(site, set()))
        for site, (_label, needed, _reason) in CLASSIFICATIONS.items()
        if not needed <= reads.get(site, set())
    }
    assert not short, f"site(s) no longer reading a channel their result carries: {short}"
