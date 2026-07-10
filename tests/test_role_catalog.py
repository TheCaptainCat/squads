"""TASK-000224: Golden-lock + packaging tests for the externalized RoleCatalogSpec (FEAT-000219).

The golden-lock test is the regression gate for FEAT-000219: it asserts the loaded
RoleCatalogSpec reproduces today's _catalog.py byte-for-byte by building a snapshot
directly from the existing PREDEFINED/BUNDLES/DEV_NAME_POOL literals and asserting
structural equality.

If this test fails, a role/bundle/dev-pool field drifted between roles.toml and the
Python literals.  Fix roles.toml (or, if intentional, update the snapshot and the TOML
together).
"""

import importlib.resources
import zipfile
from pathlib import Path

import pytest

from squads._roles._catalog import (
    BUNDLES,
    DEV_NAME_POOL,
    PREDEFINED,
    dev_role,
)
from squads._roles._loader import load_role_catalog
from squads._roles._models import RoleCatalogSpec, RoleSpec

# ---------------------------------------------------------------------------
# Frozen snapshot — built directly from today's _catalog.py literals.
# This is the independent source of truth for the golden-lock.
# ---------------------------------------------------------------------------

# Full field snapshot for all 8 roles.  Every field is listed explicitly so that
# adding a field to RoleSpec without updating this test causes a failure.
_ROLE_SNAPSHOT: list[dict[str, object]] = [
    {
        "slug": "manager",
        "full_name": "Catherine Manager",
        "title": "manager",
        "description": (
            "Default agent: triages the operator's request and routes it to the right specialist."
        ),
        "mission": (
            "Be the operator's first point of contact and run the work loop: understand the "
            "intent, delegate to the right specialists, integrate what they return, and drive "
            "each feature to done — keeping everything tracked in squads."
        ),
        "responsibilities": (
            "Triage incoming requests and clarify intent",
            "Delegate work to the right specialist agents and integrate their results",
            "Drive features through the loop (implement → review → fix) until done",
            "Keep the backlog and statuses honest",
            "Summarise progress for the operator",
        ),
        "agreements": (),
        "model": "opus",
        "color": "cyan",
        "is_default": True,
        "can_spawn": True,
    },
    {
        "slug": "architect",
        "full_name": "Robert Architect",
        "title": "architect",
        "description": "System design and architecture decisions (ADRs).",
        "mission": (
            "Own the system's shape: design coherent solutions, record decisions as ADRs, "
            "and guide implementation."
        ),
        "responsibilities": (
            "Design components and their interactions",
            "Record significant design decisions (ADRs in the bundled workflow)",
            "Author cross-cutting guides",
            "Review designs before implementation",
        ),
        "agreements": (),
        "model": "opus",
        "color": "blue",
        "is_default": False,
        "can_spawn": False,
    },
    {
        "slug": "tech-lead",
        "full_name": "Olivia Lead",
        "title": "tech lead",
        "description": "Coordination and breaking features into tasks.",
        "mission": "Turn features into well-scoped tasks, sequence the work, and unblock the team.",
        "responsibilities": (
            "Break each feature into scoped units of work, parented to the feature they "
            "implement (bundled default: `sq create task --parent FEAT-<n>`)",
            "Map each unit of work's sub-items to a single user story where the type supports "
            'it (bundled default: `sq task <n> add-subtask "…" --story USn`)',
            "For a fix or review follow-up, link via refs rather than re-describing the work "
            "(bundled default: `sq task <n> ref add <id> --kind fixes|addresses`)",
            "Leave purely-technical work items unlinked to a feature",
            "Sequence and assign work; unblock developers",
            "Co-author guides with the architect",
        ),
        "agreements": (),
        "model": "opus",
        "color": "purple",
        "is_default": False,
        "can_spawn": True,
    },
    {
        "slug": "reviewer",
        "full_name": "Paul Reviewer",
        "title": "code reviewer",
        "description": "Reviews code changes for correctness, clarity, and consistency.",
        "mission": (
            "Guard quality: review changes critically, request changes when needed, "
            "approve when sound."
        ),
        "responsibilities": (
            "Review diffs for correctness and clarity",
            "Drive code-review items to a verdict",
            "Flag risks and missing tests",
        ),
        "agreements": (
            "File review findings as tracked sub-entities — `sq review <n> add-finding` with "
            "its badge field(s) set (severity in the bundled workflow), statuses updated as "
            "they close — never as body prose; finding-scoped comments, statuses, and dossier "
            "panes all depend on the structure.",
        ),
        "model": "opus",
        "color": "red",
        "is_default": False,
        "can_spawn": False,
    },
    {
        "slug": "qa",
        "full_name": "Mara Tester",
        "title": "QA engineer",
        "description": "Designs and runs tests; verifies behaviour against acceptance criteria.",
        "mission": (
            "Prove the software works: design test cases from user stories and verify fixes."
        ),
        "responsibilities": (
            "Derive test cases from acceptance criteria (user stories in the bundled workflow)",
            "Verify fixes and features",
            "Report defects as tracked items (bug items in the bundled workflow)",
        ),
        "agreements": (),
        "model": "sonnet",
        "color": "green",
        "is_default": False,
        "can_spawn": False,
    },
    {
        "slug": "devops",
        "full_name": "Hugo Ops",
        "title": "DevOps engineer",
        "description": "CI/CD, infrastructure, and releases.",
        "mission": "Keep delivery smooth: maintain CI/CD, infrastructure, and the release process.",
        "responsibilities": (
            "Maintain CI/CD pipelines",
            "Manage infrastructure and environments",
            "Run releases",
        ),
        "agreements": (),
        "model": "sonnet",
        "color": "orange",
        "is_default": False,
        "can_spawn": False,
    },
    {
        "slug": "product-owner",
        "full_name": "Nina Product",
        "title": "product owner",
        "description": "Requirements, user stories, and backlog priorities.",
        "mission": (
            "Represent the user: capture requirements as features and user stories, "
            "prioritise the backlog."
        ),
        "responsibilities": (
            "Author features and capture requirements (`sq create feature` in the bundled "
            "workflow)",
            "Write each feature's user stories (bundled default: `sq feature <n> add-story`)",
            "Prioritise the backlog and define acceptance criteria",
        ),
        "agreements": (),
        "model": "sonnet",
        "color": "yellow",
        "is_default": False,
        "can_spawn": False,
    },
    {
        "slug": "tech-writer",
        "full_name": "Theo Writer",
        "title": "technical writer",
        "description": "Documentation and guides.",
        "mission": (
            "Make the work understandable: write and maintain clear documentation and guides."
        ),
        "responsibilities": (
            "Write user- and developer-facing docs",
            "Keep guides current",
        ),
        "agreements": (),
        "model": "haiku",
        "color": "pink",
        "is_default": False,
        "can_spawn": False,
    },
]

_BUNDLE_SNAPSHOT: dict[str, tuple[str, ...]] = {
    "all": (
        "manager",
        "architect",
        "tech-lead",
        "reviewer",
        "qa",
        "devops",
        "product-owner",
        "tech-writer",
    ),
    "core": ("manager", "architect", "tech-lead", "reviewer"),
    "minimal": ("manager",),
}

_DEV_POOL_SNAPSHOT: tuple[str, ...] = (
    "Elias",
    "Ada",
    "Linus",
    "Grace",
    "Dennis",
    "Margaret",
    "Alan",
    "Barbara",
    "Ken",
    "Edsger",
    "Radia",
    "Donald",
)

_DEV_DEFAULT_MODEL = "sonnet"
_DEV_DEFAULT_COLOR = "green"


@pytest.fixture(scope="module")
def catalog() -> RoleCatalogSpec:
    return load_role_catalog()


# ---------------------------------------------------------------------------
# Golden-lock tests (ADR-000221 §4 / TASK-224 ST1)
# ---------------------------------------------------------------------------


def test_catalog_loads_without_error(catalog: RoleCatalogSpec) -> None:
    """Smoke: the default catalog loads and passes all validation."""
    assert catalog is not None
    assert isinstance(catalog, RoleCatalogSpec)


def test_golden_role_count(catalog: RoleCatalogSpec) -> None:
    """Exactly 8 bundled roles, matching PREDEFINED count."""
    assert len(catalog.roles) == len(PREDEFINED) == 8


def test_golden_role_order(catalog: RoleCatalogSpec) -> None:
    """Declaration order preserved — slugs match PREDEFINED tuple order."""
    assert [r.slug for r in catalog.roles] == [r.slug for r in PREDEFINED]


def test_golden_snapshot_covers_all_rolespec_fields() -> None:
    """Guard: the golden snapshot covers EVERY RoleSpec field — fail if a 12th is added silently.

    The snapshot keys must equal set(RoleSpec.model_fields) so a new field never escapes the lock.
    """
    snapshot_keys = set(_ROLE_SNAPSHOT[0].keys())
    model_keys = set(RoleSpec.model_fields)
    assert snapshot_keys == model_keys, (
        f"golden snapshot does not cover all RoleSpec fields.\n"
        f"  in snapshot but not model: {snapshot_keys - model_keys}\n"
        f"  in model but not snapshot: {model_keys - snapshot_keys}"
    )


def test_golden_all_role_fields(catalog: RoleCatalogSpec) -> None:
    """Every field of every role matches the frozen snapshot."""
    assert len(catalog.roles) == len(_ROLE_SNAPSHOT), "role count mismatch"

    for spec_role, snap in zip(catalog.roles, _ROLE_SNAPSHOT, strict=True):
        slug = snap["slug"]
        assert spec_role.slug == slug, "slug mismatch at position"
        assert spec_role.full_name == snap["full_name"], f"{slug}: full_name mismatch"
        assert spec_role.title == snap["title"], f"{slug}: title mismatch"
        assert spec_role.description == snap["description"], f"{slug}: description mismatch"
        assert spec_role.mission == snap["mission"], f"{slug}: mission mismatch"
        assert tuple(spec_role.responsibilities) == snap["responsibilities"], (
            f"{slug}: responsibilities mismatch"
        )
        assert tuple(spec_role.agreements) == snap["agreements"], f"{slug}: agreements mismatch"
        assert spec_role.model == snap["model"], f"{slug}: model mismatch"
        assert spec_role.color == snap["color"], f"{slug}: color mismatch"
        assert spec_role.is_default == snap["is_default"], f"{slug}: is_default mismatch"
        assert spec_role.can_spawn == snap["can_spawn"], f"{slug}: can_spawn mismatch"


def test_golden_predefined_matches_snapshot(catalog: RoleCatalogSpec) -> None:
    """PREDEFINED tuple (the RoleDef shim) has identical field values to the snapshot."""
    assert len(PREDEFINED) == len(_ROLE_SNAPSHOT)
    for role_def, snap in zip(PREDEFINED, _ROLE_SNAPSHOT, strict=True):
        slug = snap["slug"]
        assert role_def.slug == slug
        assert role_def.full_name == snap["full_name"], f"{slug}: PREDEFINED full_name mismatch"
        assert role_def.title == snap["title"], f"{slug}: PREDEFINED title mismatch"
        assert role_def.description == snap["description"], f"{slug}: PREDEFINED desc mismatch"
        assert role_def.mission == snap["mission"], f"{slug}: PREDEFINED mission mismatch"
        assert role_def.responsibilities == snap["responsibilities"], (
            f"{slug}: PREDEFINED responsibilities mismatch"
        )
        assert role_def.agreements == snap["agreements"], f"{slug}: PREDEFINED agreements mismatch"
        assert role_def.model == snap["model"], f"{slug}: PREDEFINED model mismatch"
        assert role_def.color == snap["color"], f"{slug}: PREDEFINED color mismatch"
        assert role_def.is_default == snap["is_default"], f"{slug}: PREDEFINED is_default mismatch"
        assert role_def.can_spawn == snap["can_spawn"], f"{slug}: PREDEFINED can_spawn mismatch"


def test_golden_bundles(catalog: RoleCatalogSpec) -> None:
    """All three bundle keys and their exact membership match the snapshot."""
    assert set(catalog.bundles) == set(_BUNDLE_SNAPSHOT), (
        f"bundle keys differ: {set(catalog.bundles)!r} != {set(_BUNDLE_SNAPSHOT)!r}"
    )
    for name, expected in _BUNDLE_SNAPSHOT.items():
        actual = tuple(catalog.bundles[name])
        assert actual == expected, f"bundle {name!r}: {actual!r} != {expected!r}"
    # Also verify BUNDLES shim
    assert set(BUNDLES) == set(_BUNDLE_SNAPSHOT)
    for name, expected in _BUNDLE_SNAPSHOT.items():
        assert BUNDLES[name] == expected, f"BUNDLES[{name!r}] mismatch"


def test_golden_dev_pool(catalog: RoleCatalogSpec) -> None:
    """Dev pool (12 names + defaults) matches the snapshot and DEV_NAME_POOL constant."""
    assert tuple(catalog.dev.name_pool) == _DEV_POOL_SNAPSHOT, (
        f"dev.name_pool: {tuple(catalog.dev.name_pool)!r} != {_DEV_POOL_SNAPSHOT!r}"
    )
    assert catalog.dev.model == _DEV_DEFAULT_MODEL, (
        f"dev.model: {catalog.dev.model!r} != {_DEV_DEFAULT_MODEL!r}"
    )
    assert catalog.dev.color == _DEV_DEFAULT_COLOR, (
        f"dev.color: {catalog.dev.color!r} != {_DEV_DEFAULT_COLOR!r}"
    )
    # Verify DEV_NAME_POOL shim
    assert DEV_NAME_POOL == _DEV_POOL_SNAPSHOT, (
        f"DEV_NAME_POOL: {DEV_NAME_POOL!r} != {_DEV_POOL_SNAPSHOT!r}"
    )


def test_golden_dev_role_spotcheck() -> None:
    """dev_role('dotnet', seq=0) yields the identical RoleDef before and after externalization."""
    r = dev_role("dotnet", seq=0)
    assert r.slug == "dotnet-dev"
    assert r.full_name == "Elias Dotnet"
    assert r.title == "Dotnet developer"
    assert r.description == "Implements Dotnet code following the project's guides and standards."
    assert r.mission == (
        "Implement assigned tasks in Dotnet, following the project's guides, with tests."
    )
    assert r.responsibilities == (
        "Implement tasks in Dotnet",
        "Write tests for changes",
        "Follow the relevant guides; ask the architect when unsure",
    )
    assert r.agreements == ()
    assert r.model == "sonnet"
    assert r.color == "green"
    assert r.is_default is False
    assert r.can_spawn is False


def test_golden_default_role_is_manager(catalog: RoleCatalogSpec) -> None:
    """Exactly one role has is_default=True, and it is manager."""
    defaults = [r.slug for r in catalog.roles if r.is_default]
    assert defaults == ["manager"], f"expected ['manager'], got {defaults!r}"


def test_golden_can_spawn_roles(catalog: RoleCatalogSpec) -> None:
    """Exactly manager and tech-lead have can_spawn=True."""
    spawners = [r.slug for r in catalog.roles if r.can_spawn]
    assert set(spawners) == {"manager", "tech-lead"}, (
        f"can_spawn roles: {set(spawners)!r} != {{'manager', 'tech-lead'}}"
    )


# ---------------------------------------------------------------------------
# Packaging test (TASK-224 ST2)
# ---------------------------------------------------------------------------


def test_roles_toml_accessible_via_importlib_resources() -> None:
    """roles.toml is accessible via importlib.resources (i.e. ships as package data)."""
    pkg = importlib.resources.files("squads._roles")
    toml_path = pkg / "roles.toml"
    content = toml_path.read_bytes()
    assert content, "roles.toml is empty"
    assert b"[[roles]]" in content, "expected [[roles]] section in TOML"
    assert b"[bundles]" in content, "expected [bundles] section in TOML"
    assert b"[dev]" in content, "expected [dev] section in TOML"


def test_roles_toml_ships_in_wheel(tmp_path: Path) -> None:
    """roles.toml is present in the built wheel (package-data invariant).

    ``[tool.hatch.build.targets.wheel] packages = ["src/squads"]`` sweeps all
    non-.py files — this test confirms it actually does so.
    """
    import shutil
    import subprocess

    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not found on PATH — cannot build wheel")

    result = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"wheel build failed: {result.stderr[:300]}")

    wheels = list(tmp_path.glob("*.whl"))
    assert wheels, f"no wheel produced in {tmp_path}"

    with zipfile.ZipFile(wheels[0]) as whl:
        names = whl.namelist()

    assert any("roles.toml" in n for n in names), (
        "roles.toml not found in wheel; "
        f"files matching *roles*: {[n for n in names if 'roles' in n]}"
    )
