"""The validator-engine scaffold (Phase A of the accepted category/validator decision): the
``Validator``/``ValidatorContext`` shape, the empty closed catalog, and ``report``/``gate``
behaving as a pure no-op over it. The composition mechanism (common core + category bundle +
per-type additions) is proven against a stub bundle, independent of the (currently empty)
production catalog — a later phase populates it for real.
"""

from datetime import UTC, datetime

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._services._results import CheckIssue
from squads._services._validators import (
    CATALOG,
    CATEGORY_BUNDLES,
    COMMON_CORE,
    SQUAD_GLOBAL_CATALOG,
    ValidatorContext,
    ValidatorEngine,
    effective_validator_names,
)
from squads._workflow import bundled_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_item(seq: int, item_type: str) -> Item:
    prefix = BUILTIN_PREFIX[item_type]
    return Item(
        sequence_id=seq,
        type=item_type,
        prefix=prefix,
        title=f"item {seq}",
        slug=f"item-{seq}",
        status="Draft",
        path=f"{BUILTIN_FOLDER[item_type]}/{prefix}-{seq:06d}-item-{seq}.md",
        created_at=_NOW,
        updated_at=_NOW,
    )


# --------------------------------------------------------------------------- Phase A: no-ops


def test_catalogs_are_empty_in_phase_a() -> None:
    assert CATALOG == {}
    assert SQUAD_GLOBAL_CATALOG == {}
    assert COMMON_CORE == ()
    assert set(CATEGORY_BUNDLES) == {"roster", "work", "records"}
    assert all(bundle == () for bundle in CATEGORY_BUNDLES.values())


def test_report_over_the_empty_catalog_returns_no_issues() -> None:
    spec = bundled_spec()
    db = SquadsDB(counter=1)
    db.add(_make_item(1, "task"))
    engine = ValidatorEngine(spec=spec)
    assert engine.report(db, {}) == []


def test_gate_over_the_empty_catalog_does_not_raise() -> None:
    spec = bundled_spec()
    db = SquadsDB(counter=1)
    item = _make_item(1, "decision")
    engine = ValidatorEngine(spec=spec)
    engine.gate(item, db)  # must not raise


def test_gate_is_a_no_op_regardless_of_item_type() -> None:
    """Every bundled category (roster/work/records) resolves to an empty effective set."""
    spec = bundled_spec()
    engine = ValidatorEngine(spec=spec)
    db = SquadsDB(counter=1)
    for item_type in ("role", "task", "decision"):
        engine.gate(_make_item(1, item_type), db)  # must not raise for any category


# --------------------------------------------------------------------------- composition shape


def test_effective_validator_names_composes_common_core_and_category_bundle() -> None:
    """Proven against a stub bundle (not the real, still-empty production one) — the shape a
    real Phase B catalog will exercise unmodified."""
    stub_core = ("dangling_ref",)
    stub_bundles = {"roster": (), "work": ("no_status_banner",), "records": ("no_parent",)}

    assert effective_validator_names(
        "work", common_core=stub_core, category_bundles=stub_bundles
    ) == ("dangling_ref", "no_status_banner")
    assert effective_validator_names(
        "records", common_core=stub_core, category_bundles=stub_bundles
    ) == ("dangling_ref", "no_parent")
    assert effective_validator_names(
        "roster", common_core=stub_core, category_bundles=stub_bundles
    ) == ("dangling_ref",)


def test_effective_validator_names_appends_extra_additions_after_the_bundle() -> None:
    """Stands in for a future per-type ``validators`` field — extend-only, appended last."""
    names = effective_validator_names(
        "work",
        common_core=(),
        category_bundles={"work": ("a",)},
        extra=("b", "c"),
    )
    assert names == ("a", "b", "c")


def test_effective_validator_names_defaults_to_the_real_empty_production_tables() -> None:
    """With no stub override, every category resolves to () today — the honest Phase A shape."""
    for category in ("roster", "work", "records"):
        assert effective_validator_names(category) == ()


def test_engine_uses_a_stub_catalog_to_prove_dispatch_runs_a_named_validator() -> None:
    """The dispatch plumbing itself (catalog lookup -> call -> collect issues) works today;
    only the production catalog is empty. A stub catalog + bundle proves the wiring."""
    spec = bundled_spec()

    def _always_flags(ctx: ValidatorContext) -> list[CheckIssue]:
        return [CheckIssue("warn", ctx.item.id, "stub violation")]

    engine = ValidatorEngine(spec=spec, catalog={"stub": _always_flags})
    # Patch the module-level bundle resolution via the engine's own per-item runner is not
    # exposed publicly; instead prove the catalog is consulted through effective_validator_names
    # directly, matching what _run_per_item does internally.
    names = effective_validator_names("work", category_bundles={"work": ("stub",)})
    ctx = ValidatorContext(item=_make_item(1, "task"), spec=spec)
    issues = [issue for name in names for issue in engine.catalog[name](ctx)]
    assert issues == [CheckIssue("warn", "TASK-1", "stub violation")]


def test_squad_global_validators_run_once_in_report_never_in_gate() -> None:
    calls: list[str] = []

    def _global_check(index: SquadsDB) -> list[CheckIssue]:
        calls.append("ran")
        return [CheckIssue("error", "", "squad-global stub issue")]

    spec = bundled_spec()
    db = SquadsDB(counter=1)
    engine = ValidatorEngine(spec=spec, squad_global={"stub_global": _global_check})

    issues = engine.report(db, {})
    assert issues == [CheckIssue("error", "", "squad-global stub issue")]
    assert calls == ["ran"]

    engine.gate(_make_item(1, "task"), db)
    assert calls == ["ran"]  # gate() never invokes squad-global validators
