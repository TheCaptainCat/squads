"""Every function under ``src/squads/_cli`` that **consumes** a repair-corridor result — reads an
attribute shaped like one (``.repair``, ``.skipped``, ``.unreadable``, ``.backfill_skipped``, a
``strip_notice()`` call), or calls one of the producer methods that returns one
(``svc.sync()``, ``svc.run_pending_migrations()``, the bare-name ``svc_adopt(...)``) — must be one
of a small, fully-enumerated set of known sites, each classified as exactly one of three things: a
site that prints every channel its own consumed result type carries for this concern
(``reports-every-channel``), a site that consumes one of the target result types but prints none
of them (``reports-neither-channel`` — a defect, never a legitimate end state: no site should
carry this label once its owning command is fixed), or a site that matches the discovery pattern
syntactically without actually being a consumer of ``RepairResult``/``AdoptResult``/
``SyncSkips``'s skipped/unreadable/backfill_skipped channels (``not-a-reporting-site``).

This is family B's version of ``tests/meta/test_view_tag_writer_sites_are_exhaustively_classified``
(family A): ``sq adopt`` was the fourth consumer of the same corpus-rebuild result a three-command
hand-written list (``repair``, ``migrate up``, ``sync``) missed entirely — it read
``result.repair.strip_notice()`` and reported neither ``skipped`` nor ``unreadable``, silently,
exit 0. A hand-picked command list cannot see a consumer it never named; this test enumerates call
sites by walking the parsed source instead, so a future sixth site fails outright rather than
surviving unnoticed the way the fourth one did.

The defect class this module exists for is *consuming the sweep without reporting it*, not merely
*reading a channel field* — those are not the same filter. The first version keyed on the latter,
and it happened to catch the real fourth consumer only because ``repair`` is both a producer
method name and a channel-ish field name — a coincidence, not a property of the scan. Driven
against the scan's own ``_sites_in_module``: a constructed ``svc.sync()``-then-reads-nothing site,
a ``svc.run_pending_migrations()``-then-reads-nothing site, and a bare-name
``svc_adopt(...)``-then-reads-nothing site were all silently missed — each one precisely the
``reports-neither-channel`` state this module's own table declares must never exist. Had the real
``adopt`` discarded its result instead of reading ``result.repair``, this scan would have missed
the very defect it was built to catch. The producer method names (``sync``,
``run_pending_migrations``) are now in the discovery filter alongside the channel names, and the
bare-name producer call (``svc_adopt``) is matched the same way
``test_view_tag_writer_sites_are_exhaustively_classified`` widened its own discovery for a
bare-name ``view_tag(...)`` call — both scans were written in the same commit and only one of them
learned that lesson the first time. Not closed by this widening, and not claimed to be: a channel
read reached through ``getattr(result, ...)`` or ``dataclasses.asdict(result)`` rather than a
literal attribute access is still invisible to an AST walk that only matches ``ast.Attribute``
and a fixed producer-name set — a different, more dynamic discovery mechanism would be needed for
that shape, and none exists here.

Discovery is deliberately over-inclusive rather than narrowly typed: an AST walk has no static
type information, so it cannot tell ``result.repair`` (an ``AdoptResult``'s field) from an
unrelated ``svc.repair(...)`` service call, or ``result.strip_notice()`` (a ``RepairResult``) from
``result.strip_notice()`` on a ``RenumberResult`` (a distinct type that carries no
skipped/unreadable/backfill_skipped channel at all). Both kinds of false positive are real,
discovered sites below — classified ``not-a-reporting-site`` with a reason, not filtered out
before classification, because filtering by guessed type is exactly the kind of judgment call
that let the fourth consumer go unnoticed the first time.
"""

import ast
from pathlib import Path

# --------------------------------------------------------------------------- discovery

#: Attribute names that shape a read off a repair-corridor result value — a field
#: (``result.skipped``) or a method call whose ``.func`` is itself an ``Attribute``
#: (``result.strip_notice()``) — **plus** the producer method names that *return* one of these
#: result types in the first place (``sync``, ``run_pending_migrations``). The producer names
#: close the gap a channel-only filter cannot see by construction: a consumer that calls
#: ``svc.sync()`` and reads nothing off what comes back is still a consumer of the sweep, and
#: is exactly the ``reports-neither-channel`` shape this module exists to catch — ``sq adopt``
#: was only discovered as the fourth consumer because ``repair`` happens to double as both a
#: producer name and a channel-ish field name; a hypothetical fifth consumer built around
#: ``sync`` or ``run_pending_migrations`` alone would not have shared that coincidence.
_TARGET_ATTRS = frozenset(
    {
        "repair",
        "skipped",
        "unreadable",
        "backfill_skipped",
        "strip_notice",
        "sync",
        "run_pending_migrations",
    }
)

#: Bare-name (not attribute-style) producer calls — the same shape
#: ``test_view_tag_writer_sites_are_exhaustively_classified`` widened its own discovery for
#: (``ast.Name`` alongside ``ast.Attribute``) after the reviewer drove a bare-name writer past
#: it undetected. ``adopt`` is imported directly (``from squads._services._service import
#: adopt as svc_adopt``) rather than reached through a ``svc.`` attribute, so an attribute-only
#: filter cannot see a call to it at all, consumed or not.
_BARE_NAME_TARGETS = frozenset({"svc_adopt"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cli_root() -> Path:
    return _repo_root() / "src" / "squads" / "_cli"


def _sites_in_module(source: str, rel: str) -> set[tuple[str, str]]:
    """Every ``(module-relative-posix-path, enclosing function's qualified name)`` in *source*
    containing a target attribute read or a bare-name producer call. Takes source text directly
    (rather than a path) so the false-zero validation and the future-site falsification below
    can run it against a constructed fixture without writing a file under ``src/``."""
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
    """Validates the discovery mechanism itself against a known positive before its count of
    five sites (below) is trusted — the false-zero rule: a formatter can wrap a dotted
    attribute access across a line break (splitting on the dot), which a raw substring/line
    grep for ``"result.skipped"`` does not match but the AST walk still resolves correctly,
    because it parses structure, not lines."""
    adversarial = "def h() -> None:\n    x = (result\n        .skipped)\n"
    assert "result.skipped" not in adversarial, (
        "fixture no longer demonstrates a raw substring false zero"
    )

    found = _sites_in_module(adversarial, "adversarial.py")
    assert found == {("adversarial.py", "h")}, (
        "the AST-based scan must find an attribute read a raw substring grep misses"
    )


def test_a_newly_added_consumer_site_is_discovered_without_being_told_where_to_look() -> None:
    """Falsifies the discovery mechanism the other direction: a consumer this module has never
    seen, in a file this module has never been pointed at, must still turn up — the same
    property that makes a real sixth CLI consumer fail the exhaustiveness test below instead of
    shipping unnoticed the way ``sq adopt`` did as the fourth."""
    synthetic = (
        "async def a_brand_new_command() -> None:\n"
        "    result = await svc.some_sweep()\n"
        "    for msg in result.unreadable:\n"
        "        console.print(msg)\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_brand_new_command")}


#: The three realistic consumer shapes a channel-only filter misses, each driven against the
#: production scanner (:func:`_sites_in_module`) before the producer-name/bare-name widening —
#: control validated first (``.unreadable`` is a known positive, above), then each shape below
#: confirmed silently absent on the unwidened filter and found once the widening lands. See the
#: module docstring for why this is the defect class the label ``reports-neither-channel`` names.
def test_a_sync_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """``svc.sync()`` consumed and never read — the shape a channel-only filter cannot see
    because nothing about the return value is ever named. Caught only because ``sync`` is now
    itself a target attribute, not because of anything the call returns."""
    synthetic = (
        "async def a_quiet_sync_wrapper() -> None:\n"
        "    svc = get_service()\n"
        "    await svc.sync()\n"
        "    console.print('done')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_sync_wrapper")}


def test_a_run_pending_migrations_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """Same shape as the ``sync`` case, for ``svc.run_pending_migrations()`` — the real
    ``migrate_up`` reads ``run.applied`` and ``run.repair``, but nothing about the AST filter
    used to require that; a leaner future caller consuming only the migration side and
    discarding the trailing repair would have been invisible."""
    synthetic = (
        "async def a_quiet_migration_wrapper() -> None:\n"
        "    svc = get_service()\n"
        "    await svc.run_pending_migrations()\n"
        "    console.print('done')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_migration_wrapper")}


def test_a_bare_name_svc_adopt_call_that_reads_nothing_off_the_result_is_discovered() -> None:
    """The most on-point of the three: this is the real ``adopt`` command's own shape, minus
    the ``result.repair`` read that is the only reason the real fourth consumer was ever found.
    ``svc_adopt`` is imported directly (``from squads._services._service import adopt as
    svc_adopt``), not reached through a ``svc.`` attribute, so this also exercises the
    bare-name (``ast.Name``) half of the widening, not only the producer-name half above."""
    synthetic = (
        "async def a_quiet_adopt_wrapper() -> None:\n"
        "    await svc_adopt(squad_dir='squads')\n"
        "    console.print('adopted')\n"
    )
    found = _sites_in_module(synthetic, "squads/_cli/_not_a_real_file.py")
    assert found == {("squads/_cli/_not_a_real_file.py", "a_quiet_adopt_wrapper")}


# --------------------------------------------------------------------------- classification

#: (relative path, enclosing function) -> (classification, reason). Exactly the five sites this
#: codebase has today under ``_cli/`` — an ``AssertionError`` below for any discovered site not a
#: key here, or any key here no longer discovered, is the whole point: this dict is a
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
        "consumes SyncSkips, whose only applicable channel for this concern is "
        "backfill_skipped (RepairResult's skipped/unreadable do not apply to the narrower "
        "body-tag-only slice sync runs) — 'every channel' here means the complete channel set "
        "this result type exposes, which is the single one sync prints",
    ),
    ("squads/_cli/_main.py", "adopt"): (
        "reports-every-channel",
        "the fourth consumer the original three-command parity table missed — reads "
        "AdoptResult.repair and now prints unreadable and skipped in repair's own wording, "
        "exiting 1 on either, matching sq repair on the identical corpus",
    ),
    ("squads/_cli/_main.py", "renumber"): (
        "not-a-reporting-site",
        "matches the discovery pattern only because it calls RenumberResult.strip_notice() — "
        "a method name shared with RepairResult, not the same type. RenumberResult carries no "
        "skipped/unreadable/backfill_skipped field at all; its own 'stripped' channel is a "
        "distinct, already-covered concern (test_repair_corridor_message_and_exit_parity's "
        "strip_notice coverage), not one this enumeration is about",
    ),
}

_VALID_CLASSIFICATIONS = frozenset(
    {"reports-every-channel", "reports-neither-channel", "not-a-reporting-site"}
)


def test_every_classification_label_is_one_of_the_three_known_shapes() -> None:
    """Cheap self-check on the table above, independent of the discovery scan: catches a typo'd
    label before it could ever silently pass the completeness check below."""
    for site, (label, _reason) in CLASSIFICATIONS.items():
        assert label in _VALID_CLASSIFICATIONS, f"{site}: unknown classification {label!r}"


def test_no_site_is_classified_reports_neither_channel() -> None:
    """``reports-neither-channel`` names a defect, not a legitimate resting state (the shape
    ``sq adopt`` was in before this task's fix — silently dropping both channels, exit 0
    regardless). Nothing in the table above should ever carry it; a future consumer landing in
    that state must show up here, not merely get a fresh, uncritical classification."""
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
