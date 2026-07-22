"""The validator-engine dispatch plumbing, now fully wired: ``report``/``gate`` run the real
``COMMON_CORE``/``CATEGORY_BUNDLES`` selection over the real ``CATALOG``, and ``squad_global``
defaults to the real ``SQUAD_GLOBAL_CATALOG``. The composition mechanism itself (common core +
category bundle + per-type additions) is also proven against a stub bundle, independent of the
production tables. Per-validator parity against the legacy ``_check_*`` methods, and the
end-to-end byte-identical-set proof, live in the service-level tests.
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
from squads._workflow._models import SQUAD_GLOBAL_VALIDATOR_NAMES, VALIDATOR_NAMES

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_item(
    seq: int, item_type: str, *, status: str = "Draft", author: str | None = None
) -> Item:
    prefix = BUILTIN_PREFIX[item_type]
    return Item(
        sequence_id=seq,
        type=item_type,
        prefix=prefix,
        title=f"item {seq}",
        slug=f"item-{seq}",
        status=status,
        author=author,
        path=f"{BUILTIN_FOLDER[item_type]}/{prefix}-{seq:06d}-item-{seq}.md",
        created_at=_NOW,
        updated_at=_NOW,
    )


# --------------------------------------------------------------------------- catalog/bundle shape


def test_catalogs_implement_exactly_the_declared_name_registries() -> None:
    assert set(CATALOG) == VALIDATOR_NAMES
    assert set(SQUAD_GLOBAL_CATALOG) == SQUAD_GLOBAL_VALIDATOR_NAMES


def test_common_core_and_category_bundles_are_populated() -> None:
    """``no_parent`` on ``records``/``epic`` is deliberately withheld — a separate,
    migration-sequenced task."""
    assert set(COMMON_CORE) == {
        "item_status_valid",
        "dangling_ref",
        "ref_kind_valid",
        "no_status_banner",
        "agent_registered",
    }
    assert set(CATEGORY_BUNDLES) == {"roster", "work", "records"}
    assert CATEGORY_BUNDLES["roster"] == ()
    assert "no_parent" not in CATEGORY_BUNDLES["records"]
    assert "parent_in" in CATEGORY_BUNDLES["work"]
    assert "no_parent" not in CATEGORY_BUNDLES["work"]


# --------------------------------------------------------------------------- report/gate, wired


def test_report_runs_the_real_bundles_over_a_clean_item() -> None:
    """Squad-global excluded here (needs ``paths`` — see the dedicated test below); this one
    isolates the real per-item common-core + category-bundle selection."""
    spec = bundled_spec()
    db = SquadsDB(counter=1)
    db.add(_make_item(1, "task"))
    engine = ValidatorEngine(spec=spec, squad_global={})
    assert engine.report(db, {}) == []


def test_gate_does_not_raise_for_a_clean_item() -> None:
    spec = bundled_spec()
    db = SquadsDB(counter=1)
    item = _make_item(1, "decision", status="Proposed")
    db.add(item)
    engine = ValidatorEngine(spec=spec)
    engine.gate(item, db)  # must not raise


def test_gate_raises_on_an_error_level_violation() -> None:
    from squads._errors import SquadsError

    spec = bundled_spec()
    db = SquadsDB(counter=1)
    item = _make_item(1, "decision", status="NotAStatus")
    engine = ValidatorEngine(spec=spec)
    try:
        engine.gate(item, db)
    except SquadsError as e:
        assert "invalid for decision" in str(e)
    else:
        raise AssertionError("expected a SquadsError")


def test_gate_never_raises_on_a_warn_only_violation() -> None:
    """``agent_registered`` is warn-level — an unregistered author never aborts the gate."""
    spec = bundled_spec()
    db = SquadsDB(counter=1)
    item = _make_item(1, "task", author="nobody", status="Draft")
    engine = ValidatorEngine(spec=spec)
    engine.gate(item, db)  # must not raise


# --------------------------------------------------------------------------- composition shape


def test_effective_validator_names_composes_common_core_and_category_bundle() -> None:
    """Proven against a stub bundle (not production) — the shape a real catalog exercises."""
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
    """Stands in for the per-type ``validators`` field (the assignment-surface task) —
    extend-only, appended last."""
    names = effective_validator_names(
        "work",
        common_core=(),
        category_bundles={"work": ("a",)},
        extra=("b", "c"),
    )
    assert names == ("a", "b", "c")


def test_effective_validator_names_matches_the_real_production_tables() -> None:
    for category in ("roster", "work", "records"):
        assert effective_validator_names(category) == COMMON_CORE + CATEGORY_BUNDLES[category]


def test_engine_uses_a_stub_catalog_to_prove_dispatch_runs_a_named_validator() -> None:
    """The dispatch plumbing itself (catalog lookup -> call -> collect issues), proven with a
    stub name/bundle so it's independent of whatever the real catalog/bundles contain."""
    spec = bundled_spec()

    def _always_flags(ctx: ValidatorContext) -> list[CheckIssue]:
        return [CheckIssue("warn", ctx.item.id, "stub violation")]

    engine = ValidatorEngine(spec=spec, catalog={"stub": _always_flags})
    names = effective_validator_names("work", common_core=(), category_bundles={"work": ("stub",)})
    ctx = ValidatorContext(item=_make_item(1, "task"), spec=spec)
    issues = [issue for name in names for issue in engine.catalog[name](ctx)]
    assert issues == [CheckIssue("warn", "TASK-1", "stub violation")]


def test_squad_global_validators_run_once_in_report_never_in_gate(tmp_path) -> None:
    from squads._models._config import SquadsConfig
    from squads._paths import SquadPaths
    from squads._services._validators import SquadGlobalContext

    calls: list[str] = []

    def _global_check(ctx: SquadGlobalContext) -> list[CheckIssue]:
        calls.append("ran")
        return [CheckIssue("error", "", "squad-global stub issue")]

    spec = bundled_spec()
    db = SquadsDB(counter=1)
    paths = SquadPaths(root=tmp_path, squad_dir=tmp_path, config=SquadsConfig())
    engine = ValidatorEngine(spec=spec, paths=paths, squad_global={"stub_global": _global_check})

    issues = engine.report(db, {})
    assert issues == [CheckIssue("error", "", "squad-global stub issue")]
    assert calls == ["ran"]

    engine.gate(_make_item(1, "task"), db)
    assert calls == ["ran"]  # gate() never invokes squad-global validators


def test_squad_global_defaults_to_the_real_catalog() -> None:
    engine = ValidatorEngine(spec=bundled_spec())
    assert engine.squad_global == SQUAD_GLOBAL_CATALOG


def test_report_requires_paths_only_when_squad_global_is_non_empty() -> None:
    """A bare ``ValidatorEngine(spec=...)`` now defaults ``squad_global`` to the real
    catalog, so calling ``report()`` with no ``paths`` fails closed instead of silently
    skipping the squad-global class."""
    from squads._errors import SquadsError

    engine = ValidatorEngine(spec=bundled_spec())
    db = SquadsDB(counter=1)
    try:
        engine.report(db, {})
    except SquadsError as e:
        assert "paths" in str(e)
    else:
        raise AssertionError("expected a SquadsError")
