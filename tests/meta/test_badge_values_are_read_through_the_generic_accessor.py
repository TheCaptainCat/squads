"""Repo-hygiene gate: a stored badge value is read through ``badge_value``, never through
``getattr(entity, field.code)``.

Two of the declared badge field codes — ``priority`` and ``severity`` — happen to be real
attributes on ``Item``; every other declared code, including every code an adopter declares,
lives in the generic ``extra`` store. So ``getattr(obj, f.code, None)`` reads the two bundled
ones and silently returns ``None`` for all the rest, which does not look like a bug at any call
site: the loop runs, the two familiar fields validate, and the adopter's field is skipped.

It cost the load boundary its whole purpose for adopter-declared fields. Driven on the same
operation, both directions: shrinking the bundled ``priority`` collection under a live item
made every command exit 1 naming the item; shrinking an override-declared ``impact``
collection with ``extra.impact`` stored left ``sq list -a`` at exit 0, ``sq workflow lint``
reporting OK and ``sq check`` silent, with the item keeping an undeclared code indefinitely.

``Item.badge_value`` / ``SubEntity.badge_value`` exist for exactly this and read both stores.
The scan is textual and narrow — a ``getattr`` whose attribute argument is a field's own
``.code`` — because that is the precise returning shape, and a broader "no ``getattr`` here"
rule would flag the many legitimate dynamic reads in the same files.
"""

import re
from pathlib import Path

#: ``getattr(<anything>, <anything>.code …)`` — a dynamic read keyed by a spec field's code.
#: The attribute expression is what makes this specific: a field/badge object's ``.code`` is
#: only ever a *declared* code, so using it as an attribute name is the assumption this forbids.
_GETATTR_BY_FIELD_CODE_RE = re.compile(r"getattr\(\s*[^,()]+,\s*[A-Za-z_][A-Za-z0-9_.]*\.code\b")

#: Every source file under this tree is scanned.
_SCANNED_TREE = ("src", "squads")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _hits(root: Path) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for path in sorted((root.joinpath(*_SCANNED_TREE)).rglob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        numbers = [n for n, line in enumerate(lines, 1) if _GETATTR_BY_FIELD_CODE_RE.search(line)]
        if numbers:
            found[path.relative_to(root).as_posix()] = numbers
    return found


def test_no_source_file_reads_a_badge_value_by_getattr_on_its_field_code() -> None:
    hits = _hits(_repo_root())
    assert not hits, (
        "a stored badge value is read with getattr(obj, <field>.code) — that skips every "
        "declared field without a same-named model attribute, which is every adopter-declared "
        "one. Use obj.badge_value(<field>.code) instead: "
        f"{hits}"
    )


def test_the_scan_recognises_the_shape_it_forbids() -> None:
    """The guard's own liveness: a scan that matches nothing because its pattern is wrong
    passes exactly as loudly as one with nothing to find."""
    planted = "        code = getattr(obj, f.code, None)\n"
    assert _GETATTR_BY_FIELD_CODE_RE.search(planted)
    assert _GETATTR_BY_FIELD_CODE_RE.search("value = getattr(sub, field.code, None)")
    # …and does not fire on the accessor that replaced it, nor on unrelated dynamic reads.
    assert not _GETATTR_BY_FIELD_CODE_RE.search("code = obj.badge_value(f.code)")
    assert not _GETATTR_BY_FIELD_CODE_RE.search("slug = getattr(ctx.item, attr)")


def test_both_entity_types_expose_the_accessor_the_guard_points_at() -> None:
    """Behavioural half: the scan is only meaningful while ``badge_value`` actually reads the
    generic store, so pin that rather than assuming the name still means what it says."""
    from datetime import UTC, datetime

    from squads._models._item import Item
    from squads._models._subentity import SubEntity

    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = Item(
        sequence_id=1,
        type="bug",
        title="t",
        slug="t",
        status="Draft",
        path="bugs/x.md",
        created_at=now,
        updated_at=now,
    )
    item.set_badge_value("impact", "high")
    assert item.badge_value("impact") == "high"  # no same-named attribute — read from extra
    item.set_badge_value("priority", "urgent")
    assert item.badge_value("priority") == "urgent"  # real attribute — read from the field

    sub = SubEntity(local_id="ST1", title="s", status="Todo")
    sub.set_badge_value("impact", "low")
    assert sub.badge_value("impact") == "low"
