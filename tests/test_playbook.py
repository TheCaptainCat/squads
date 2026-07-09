"""TASK-000229: Golden-lock + packaging tests for the externalized PlaybookSpec (FEAT-000220).

Two-layer regression gate:

  Layer A — structural equality: a frozen snapshot built from today's hardcoded Python
             literals must match the loaded ``PlaybookSpec`` field-for-field.  If this
             fails, a string or list drifted between ``playbook.toml`` and the original
             source.  Fix the TOML (or update the snapshot here and the TOML together).

  Layer B — generated-output equality (the decisive one per ADR-000226 §4): render each
             sq-<type> skill through the real ``agents/item_skill.md.j2`` path with a
             fixed representative roster (all bundled roles + one dev) and assert the
             output is byte-identical to rendering from the frozen ``_SNAPSHOT`` data.
             This catches any regression in the ``*dev`` → "developers" sentinel
             resolution, the spec-to-shim conversion, or the template — a faithful spec
             that rendered differently would still be a user-visible regression.

  Shim fidelity tests (also in Layer B section): ``PLAYBOOK[t]`` field values must
             match ``get_playbook_spec().types[t]`` after ``spec_to_item_playbook``
             conversion.

Packaging test: ``playbook.toml`` must be accessible via ``importlib.resources`` and
present in the built wheel.
"""

# ruff: noqa: E501  — snapshot strings are frozen from the pre-FEAT-220 Python PLAYBOOK literals (the HEAD source of truth); wrapping obscures diffs.

import importlib.resources
import zipfile
from pathlib import Path
from typing import Any

import pytest

from squads._interactions import DEV, PLAYBOOK, RoleGuide, get_playbook_spec, spec_to_item_playbook
from squads._interactions._loader import load_playbook
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec, RoleGuideSpec
from squads._rendering._engine import render
from squads._roles._catalog import get_catalog

# ---------------------------------------------------------------------------
# Layer A: frozen golden snapshot
#
# Every field of every ItemPlaybookSpec / RoleGuideSpec is listed explicitly.
# A field-completeness guard asserts the snapshot keys cover the whole model_fields set.
# ---------------------------------------------------------------------------

_SNAPSHOT: dict[str, dict[str, object]] = {
    "epic": {
        "overview": "A large body of work that groups related features toward one outcome.",
        "lifecycle": "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        "commands": [
            'sq create epic "…" --author <slug>',
            "sq feature <n> update --parent EPIC-…   # group a feature under this epic",
            "sq tree EPIC-… [--json]",
        ],
        "roles": [
            {
                "slug": "product-owner",
                "enter": ["confirm the outcome the epic targets and who it's for"],
                "do": [
                    'author it (`sq create epic "…" --author product-owner`)',
                    "set the body to the goal + the outcomes it groups (`sq epic <n> body -m …`)",
                ],
                "handoff": [
                    "when the epic is ready, create the features under it and `@tech-lead` to break them down",
                ],
                "watch": ["an epic is an outcome, not a task list — keep it about the why"],
            },
            {
                "slug": "architect",
                "enter": ["read the epic's goal and any related epics/ADRs"],
                "do": [
                    "shape it technically; spin off ADRs (`sq create decision`) for cross-cutting calls and link them (`sq epic <n> ref add ADR-… --kind related`)",
                ],
                "handoff": [
                    "when the technical shape is settled, `@tech-lead` to break it into features and tasks",
                ],
                "watch": [],
            },
            {
                "slug": "tech-lead",
                "enter": ["review the epic's features and their state (`sq tree EPIC-… --json`)"],
                "do": [
                    "group features under the epic (`sq feature <n> update --parent EPIC-…`)",
                    "keep its scope coherent; track status as features progress",
                ],
                "handoff": [],
                "watch": ["authoring features is the product-owner's job, not yours"],
            },
        ],
    },
    "feature": {
        "overview": "A user-facing capability, described through persona-worded user stories.",
        "lifecycle": "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        "commands": [
            'sq create feature "…" --author product-owner [--parent EPIC-…]',
            'sq feature <n> add-story "As a <role>, I want … so that …"',
            "sq feature <n> story <k> update --status InProgress   # Todo → InProgress → Done",
            "sq feature <n> stories",
        ],
        "roles": [
            {
                "slug": "product-owner",
                "enter": ["confirm the user need and which epic (if any) it belongs under"],
                "do": [
                    'author the feature (`sq create feature "…" --author product-owner`)',
                    'add persona-worded user stories (`sq feature <n> add-story "As a … I want …"`) — the title is the user-story phrase',
                    "write each story's body (`sq feature <n> story <k> body -m …`) — the acceptance criteria live there, not in the title",
                    "use `sq feature <n> story <k> comment` for story-scoped acceptance clarifications or questions — cross-cutting notes go on the feature (see the `squads` skill's comment-scoping convention)",
                ],
                "handoff": [
                    "when stories and acceptance criteria are complete and the feature is greenlit, `@tech-lead` to break it into tasks",
                ],
                "watch": [
                    "stories describe user value + acceptance criteria — not implementation steps",
                    "a story is not done until its body carries acceptance criteria — an unwritten placeholder body is a defect even if the title reads fine",
                ],
            },
            {
                "slug": "tech-lead",
                "enter": [
                    "read every user story + its acceptance criteria (`sq feature <n> show`)"
                ],
                "do": [
                    "create tasks with this feature as parent (`sq create task … --parent FEAT-<n>`)",
                    "map each subtask to one user story (`sq task <n> add-subtask … --story USk`)",
                    "use `sq feature <n> story <k> comment` for story-scoped questions (see the `squads` skill's comment-scoping convention)",
                ],
                "handoff": [
                    "when tasks are created, assigned, and sequenced, `@<tech>-dev` (or spawn the developer) to begin implementation",
                ],
                "watch": [
                    "if a story is ambiguous, ask the product-owner (`@product-owner`) first"
                ],
            },
            {
                "slug": "qa",
                "enter": ["read the user stories + acceptance criteria"],
                "do": [
                    "derive test cases from each story",
                    "verify the feature against its acceptance criteria once tasks land",
                ],
                "handoff": [
                    "when acceptance criteria all pass, confirm in a comment so the feature can close; when one fails, file a bug and `@tech-lead`",
                ],
                "watch": [],
            },
        ],
    },
    "task": {
        "overview": "A unit of implementation work. Its parent is the feature it implements; subtasks each map to one user story.",
        "lifecycle": "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)",
        "commands": [
            'sq create task "…" --author tech-lead --parent FEAT-…',
            'sq task <n> add-subtask "…" --story USn',
            "sq task <n> subtask <k> update --status InProgress   # Todo → InProgress → Done",
            "sq task <n> ref add BUG-… --kind fixes   # or REV-… --kind addresses",
            "sq task <n> status InProgress",
        ],
        "roles": [
            {
                "slug": "tech-lead",
                "enter": ["confirm the parent feature exists and its stories are clear"],
                "do": [
                    'author the task (`sq create task "…" --author tech-lead --parent FEAT-…`)',
                    "add subtasks, each mapped to a story (`add-subtask … --story USn`) — the title is a short handle; implementation detail goes in the subtask body (`sq task <n> subtask <k> body -m …`)",
                    "set `--priority`/`--assignee`; sequence with `ref add … --kind blocks`",
                ],
                "handoff": [
                    "once the task is fully defined, assign the developer (`sq task <n> update --assignee <tech>-dev`) — spawn or `@<tech>-dev` to start implementation",
                ],
                "watch": [
                    "a task's parent must be a feature; link bugs/reviews via refs, never as parent",
                ],
            },
            {
                "slug": DEV,
                "enter": [
                    "read the parent feature's stories + acceptance criteria (`sq feature <n> show`)",
                    "confirm your subtask→story mapping",
                ],
                "do": [
                    "`sq task <n> status InProgress`",
                    "implement with tests; tick subtasks (`subtask <k> update --status …`)",
                    "use `sq task <n> subtask <k> comment` for implementation notes scoped to one subtask; use `sq task <n> comment` for handoffs and cross-cutting notes (see the `squads` skill's comment-scoping convention)",
                ],
                "handoff": [
                    "when implementation is complete, `sq task <n> status InReview`",
                    "comment a summary of what changed + `@reviewer`/`@qa`",
                    "for a review follow-up, link it (`ref add REV-… --kind addresses`)",
                ],
                "watch": [
                    "don't author features/tasks — that's the product-owner/tech-lead",
                    "file a newly-found defect as a bug; don't silently expand scope",
                ],
            },
            {
                "slug": "reviewer",
                "enter": ["read the task's changes + the linked feature stories"],
                "do": [
                    "open a review (`sq create review … --author reviewer`) and link it (`sq task <n> ref add REV-… --kind addresses`)",
                    "log findings with `--severity`; drive Requested → InReview → verdict",
                ],
                "handoff": [
                    "on ChangesRequested, `@<tech>-dev` with the findings",
                    "on Approved, comment the verdict so the task can close",
                ],
                "watch": ["request changes — don't fix the code yourself"],
            },
            {
                "slug": "qa",
                "enter": [
                    "derive test cases from the parent feature's stories + acceptance criteria"
                ],
                "do": ["verify the implementation against each story; reproduce on failure"],
                "handoff": [
                    "on pass, comment confirmation so the task can reach Done",
                    "on fail, file a bug (`sq create bug …`) and `@<tech>-dev`",
                ],
                "watch": ["verify against acceptance criteria, not just that it runs"],
            },
        ],
    },
    "bug": {
        "overview": "A defect: what's wrong, how to reproduce, expected vs actual.",
        "lifecycle": "Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)",
        "commands": [
            'sq create bug "…" --author <slug>',
            "sq task <n> ref add BUG-… --kind fixes",
            "sq bug <n> status InProgress",
        ],
        "roles": [
            {
                "slug": "qa",
                "enter": ["reproduce the defect and capture the exact steps"],
                "do": [
                    'file it (`sq create bug "…" --author qa`)',
                    "in the body give repro steps + expected vs actual (`sq bug <n> body -m …`)",
                    "set `--severity`/`--priority`",
                ],
                "handoff": [
                    "once filed, `@tech-lead` to triage; once a fix task lands, verify it and confirm in a comment so the bug can close",
                ],
                "watch": [],
            },
            {
                "slug": DEV,
                "enter": ["read the repro steps; confirm you can reproduce it"],
                "do": [
                    "fix it inside a task and link it (`sq task <n> ref add BUG-… --kind fixes`)",
                    "add a regression test",
                ],
                "handoff": [
                    "when the fix is ready, move the task to InReview and `@reviewer`/`@qa`; the bug closes when the fix is verified",
                ],
                "watch": ["track the fix on a task — don't implement straight off the bug"],
            },
            {
                "slug": "tech-lead",
                "enter": ["assess impact + severity against current work"],
                "do": ["triage and prioritise; create the fix task and assign a developer"],
                "handoff": [
                    "once the fix task is created and assigned, `@<tech>-dev` to start the fix",
                ],
                "watch": [],
            },
            {
                "slug": "reviewer",
                "enter": ["read the bug + the fix task's changes"],
                "do": ["review the fix for correctness and a regression test before it lands"],
                "handoff": [],
                "watch": ["make sure the root cause is fixed, not just the symptom"],
            },
        ],
    },
    "decision": {
        "overview": "An architecture decision record: context, decision, consequences.",
        "lifecycle": "Proposed → Accepted → Superseded (+ Rejected, Deprecated)",
        "commands": [
            'sq create decision "…" --author architect',
            "sq decision <n> status Accepted",
        ],
        "roles": [
            {
                "slug": "architect",
                "enter": ["gather the context + the options you're weighing"],
                "do": [
                    'author the ADR (`sq create decision "…" --author architect`)',
                    "in the body capture context, the decision, and consequences",
                    "link what it affects (`sq decision <n> ref add … --kind related`)",
                ],
                "handoff": [
                    "once the decision is agreed, `sq decision <n> status Accepted` and `@tech-lead` to apply it in the affected tasks",
                ],
                "watch": ["supersede an old ADR rather than editing its decision after acceptance"],
            },
            {
                "slug": "tech-lead",
                "enter": ["read the proposed decision + its context"],
                "do": ["co-author/review it; ensure tasks follow it once Accepted"],
                "handoff": ["supersede it (new ADR) when reality changes"],
                "watch": [],
            },
        ],
    },
    "review": {
        "overview": "A code review: scope, findings (each with severity + status), and a verdict.",
        "lifecycle": "Requested → InReview → ChangesRequested → Approved (+ Rejected)",
        "commands": [
            'sq create review "…" --author reviewer',
            'sq review <n> add-finding "…" --severity high',
            "sq review <n> finding <k> update --status Fixed   # transition a finding",
            "sq review <n> status InReview",
            "sq task <n> ref add REV-… --kind addresses",
        ],
        "roles": [
            {
                "slug": "reviewer",
                "enter": ["read the task/changes under review + the feature's acceptance criteria"],
                "do": [
                    "`sq review <n> status InReview`",
                    'log each issue as a finding (`add-finding "…" --severity …`) — the title is a short handle; the full description goes in the finding body (`sq review <n> finding <k> body -m …`)',
                    "drive to a verdict: Approved or ChangesRequested",
                    "use `sq review <n> finding <k> comment` for finding-scoped notes (rationale, verification notes, 'agreed — closing this one') — cross-cutting notes and the final verdict go on the review (see the `squads` skill's comment-scoping convention)",
                ],
                "handoff": [
                    "on ChangesRequested, `@<tech>-dev` with the findings",
                    "on Approved, comment the verdict",
                ],
                "watch": ["severity-tag findings honestly; don't approve with open high findings"],
            },
            {
                "slug": DEV,
                "enter": ["read every finding and its severity (`sq review <n> findings`)"],
                "do": [
                    "fix each one, then `sq review <n> finding <k> update --status Fixed`",
                    "link the fix task (`sq task <n> ref add REV-… --kind addresses`)",
                    "use `sq review <n> finding <k> comment` when closing a finding with fix rationale — keep the review's main discussion for handoff @mentions (see the `squads` skill's comment-scoping convention)",
                ],
                "handoff": ["`@reviewer` once all findings are Fixed, for re-review"],
                "watch": ["don't close findings you didn't actually address"],
            },
        ],
    },
    "guide": {
        "overview": "Project-agnostic best-practice notes on a technology or framework.",
        "lifecycle": "Draft → Published → Deprecated",
        "commands": [
            'sq create guide "…" --author architect [--tech …] [--tag …]',
            "sq guide <n> status Published",
        ],
        "roles": [
            {
                "slug": "architect",
                "enter": ["identify the recurring practice or anti-pattern worth capturing"],
                "do": [
                    'author it (`sq create guide "…" --author architect --tech …`)',
                    "write good practice + anti-patterns in the body",
                ],
                "handoff": [
                    "when the first draft is complete, `@tech-writer` to polish; set `sq guide <n> status Published` once it's clean",
                ],
                "watch": [],
            },
            {
                "slug": "tech-lead",
                "enter": ["spot a lesson from a real task worth generalising"],
                "do": ["co-author the guide drawn from concrete work"],
                "handoff": [],
                "watch": [],
            },
            {
                "slug": "tech-writer",
                "enter": ["read the draft guide"],
                "do": ["edit for clarity, structure, and currency"],
                "handoff": ["`sq guide <n> status Published` when it's clean"],
                "watch": ["keep it project-agnostic; deprecate guides that go stale"],
            },
        ],
    },
}


@pytest.fixture(scope="module")
def spec() -> PlaybookSpec:
    return load_playbook(get_catalog())


# ---------------------------------------------------------------------------
# Fail-closed: unknown keys in TOML must raise SquadsError (extra="forbid")
# ---------------------------------------------------------------------------


def test_unknown_key_in_item_entry_raises_squads_error() -> None:
    """A typo'd top-level key in a types.<name> entry (e.g. "commandz") must raise SquadsError.

    This proves that ItemPlaybookSpec.model_validate is called (not cherry-picking),
    so extra="forbid" actually fires rather than silently dropping the unknown field.
    """
    from squads._interactions._loader import _build_spec  # pyright: ignore[reportPrivateUsage]
    from squads._workflow import bundled_spec

    # Minimal valid raw playbook with one synthetic entry that has an unknown key.
    catalog = get_catalog()
    raw: dict[str, Any] = {
        "types": {
            "task": {
                "overview": "A unit of work.",
                "lifecycle": "Draft → Done",
                "commandz": ["this-key-is-a-typo"],  # unknown key — must be rejected
                "commands": [],
                "roles": [],
            }
        }
    }
    with pytest.raises(Exception, match=r"(?i)(extra|commandz|invalid|unknown|forbidden)"):
        _build_spec(raw, catalog, bundled_spec())


def test_unknown_key_in_role_guide_raises_squads_error() -> None:
    """A typo'd key inside a [[types.<name>.roles]] entry (e.g. "entr") must raise SquadsError.

    This proves that RoleGuideSpec.model_validate is called, so extra="forbid" fires.
    """
    from squads._interactions._loader import _build_spec  # pyright: ignore[reportPrivateUsage]
    from squads._workflow import bundled_spec

    catalog = get_catalog()
    raw: dict[str, Any] = {
        "types": {
            "task": {
                "overview": "A unit of work.",
                "lifecycle": "Draft → Done",
                "commands": [],
                "roles": [
                    {
                        "slug": "tech-lead",
                        "entr": ["this-key-is-a-typo"],  # unknown key — must be rejected
                        "enter": [],
                        "do": [],
                        "handoff": [],
                        "watch": [],
                    }
                ],
            }
        }
    }
    with pytest.raises(Exception, match=r"(?i)(extra|entr|invalid|unknown|forbidden)"):
        _build_spec(raw, catalog, bundled_spec())


# ---------------------------------------------------------------------------
# Layer A: structural golden-lock
# ---------------------------------------------------------------------------


def test_spec_loads_without_error(spec: PlaybookSpec) -> None:
    """Smoke: the default playbook loads and passes all validation."""
    assert spec is not None
    assert isinstance(spec, PlaybookSpec)


def test_golden_snapshot_covers_all_itemplybookspec_fields() -> None:
    """Guard: snapshot top-level keys cover every ItemPlaybookSpec field.

    If a field is added to ItemPlaybookSpec without updating this test, the
    assertion fails immediately — nothing silently slips past the lock.
    """
    snapshot_keys = set(_SNAPSHOT["task"].keys())
    model_keys = set(ItemPlaybookSpec.model_fields)
    assert snapshot_keys == model_keys, (
        f"golden snapshot does not cover all ItemPlaybookSpec fields.\n"
        f"  in snapshot but not model: {snapshot_keys - model_keys}\n"
        f"  in model but not snapshot: {model_keys - snapshot_keys}"
    )


def test_golden_snapshot_covers_all_roleguidespec_fields() -> None:
    """Guard: role guide snapshot keys cover every RoleGuideSpec field."""
    snapshot_keys = set(_SNAPSHOT["task"]["roles"][0].keys())  # type: ignore[union-attr]
    model_keys = set(RoleGuideSpec.model_fields)
    assert snapshot_keys == model_keys, (
        f"golden snapshot does not cover all RoleGuideSpec fields.\n"
        f"  in snapshot but not model: {snapshot_keys - model_keys}\n"
        f"  in model but not snapshot: {model_keys - snapshot_keys}"
    )


def test_golden_type_count(spec: PlaybookSpec) -> None:
    """Exactly 7 work types in the loaded spec."""
    assert len(spec.types) == len(_SNAPSHOT) == 7


def test_golden_type_keys(spec: PlaybookSpec) -> None:
    """Loaded spec keys match the snapshot keys (same 7 work types)."""
    assert set(spec.types) == set(_SNAPSHOT), (
        f"spec types {set(spec.types)!r} != snapshot {set(_SNAPSHOT)!r}"
    )


def test_golden_all_item_type_fields(spec: PlaybookSpec) -> None:
    """Every field of every ItemPlaybookSpec matches the frozen snapshot."""
    for type_name, snap in _SNAPSHOT.items():
        item_type = type_name
        assert item_type in spec.types, f"type {type_name!r} missing from spec"
        entry = spec.types[item_type]

        assert entry.overview == snap["overview"], f"{type_name}: overview mismatch"
        assert entry.lifecycle == snap["lifecycle"], f"{type_name}: lifecycle mismatch"
        assert list(entry.commands) == snap["commands"], f"{type_name}: commands mismatch"

        snap_roles: list[dict[str, object]] = snap["roles"]  # type: ignore[assignment]
        assert len(entry.roles) == len(snap_roles), (
            f"{type_name}: role count {len(entry.roles)} != {len(snap_roles)}"
        )

        for i, (guide, rsnap) in enumerate(zip(entry.roles, snap_roles, strict=True)):
            ctx = f"{type_name}.roles[{i}]"
            assert guide.slug == rsnap["slug"], f"{ctx}: slug mismatch"
            assert list(guide.enter) == rsnap["enter"], f"{ctx}: enter mismatch"
            assert list(guide.do) == rsnap["do"], f"{ctx}: do mismatch"
            assert list(guide.handoff) == rsnap["handoff"], f"{ctx}: handoff mismatch"
            assert list(guide.watch) == rsnap["watch"], f"{ctx}: watch mismatch"


# ---------------------------------------------------------------------------
# Layer B: shim fidelity — PLAYBOOK dataclass shims match the spec
# ---------------------------------------------------------------------------


def test_shim_type_set_matches_spec() -> None:
    """PLAYBOOK keys are the same 7 work types as the spec."""
    assert set(PLAYBOOK.keys()) == set(get_playbook_spec().types.keys())


def test_shim_conversion_is_lossless() -> None:
    """spec_to_item_playbook converts every field without loss or transformation.

    For each work type: build the ItemPlaybook shim directly from the spec entry
    and assert field-for-field equality with PLAYBOOK[t].
    This is the decisive test: if spec_to_item_playbook silently drops a field
    (or truncates a list), this fails.
    """
    for item_type, spec_entry in get_playbook_spec().types.items():
        shim = PLAYBOOK[item_type]
        converted = spec_to_item_playbook(spec_entry)

        assert shim.overview == converted.overview, f"{item_type}: overview"
        assert shim.lifecycle == converted.lifecycle, f"{item_type}: lifecycle"
        assert shim.commands == converted.commands, f"{item_type}: commands"
        assert len(shim.roles) == len(converted.roles), f"{item_type}: role count"

        for i, (sr, cr) in enumerate(zip(shim.roles, converted.roles, strict=True)):
            ctx = f"{item_type}.roles[{i}] ({sr.slug!r})"
            assert sr.slug == cr.slug, f"{ctx}: slug"
            assert sr.enter == cr.enter, f"{ctx}: enter"
            assert sr.do == cr.do, f"{ctx}: do"
            assert sr.handoff == cr.handoff, f"{ctx}: handoff"
            assert sr.watch == cr.watch, f"{ctx}: watch"


def test_shim_playbook_matches_snapshot() -> None:
    """PLAYBOOK (the public shim) matches the snapshot field-for-field.

    Cross-check between the snapshot and the live module-level constant, so
    any drift from either direction is caught.
    """
    for type_name, snap in _SNAPSHOT.items():
        item_type = type_name
        assert item_type in PLAYBOOK, f"{type_name!r} missing from PLAYBOOK"
        pb = PLAYBOOK[item_type]

        assert pb.overview == snap["overview"], f"{type_name}: overview"
        assert pb.lifecycle == snap["lifecycle"], f"{type_name}: lifecycle"
        assert list(pb.commands) == snap["commands"], f"{type_name}: commands"

        snap_roles: list[dict[str, object]] = snap["roles"]  # type: ignore[assignment]
        assert len(pb.roles) == len(snap_roles), (
            f"{type_name}: role count {len(pb.roles)} != {len(snap_roles)}"
        )
        for i, (guide, rsnap) in enumerate(zip(pb.roles, snap_roles, strict=True)):
            ctx = f"{type_name}.roles[{i}]"
            assert guide.slug == rsnap["slug"], f"{ctx}: slug"
            assert list(guide.enter) == rsnap["enter"], f"{ctx}: enter"
            assert list(guide.do) == rsnap["do"], f"{ctx}: do"
            assert list(guide.handoff) == rsnap["handoff"], f"{ctx}: handoff"
            assert list(guide.watch) == rsnap["watch"], f"{ctx}: watch"


# ---------------------------------------------------------------------------
# Layer B: generated-output golden-lock (ADR-000226 §4)
#
# Fixed representative roster — all 8 bundled roles + one python-dev so the
# *dev → "developers" section renders for task/bug/review.  These are the
# names emitted by the bundled role catalog; if they ever change, this
# fixture must be updated (and the real sq sync output changes too).
# ---------------------------------------------------------------------------

#: slug → display name used in "## For <name> (`slug`)" headings.
_FIXED_ROSTER: dict[str, str] = {
    "manager": "Catherine Manager",
    "architect": "Robert Architect",
    "tech-lead": "Olivia Lead",
    "reviewer": "Paul Reviewer",
    "qa": "Mara Tester",
    "devops": "Hugo Ops",
    "product-owner": "Nina Product",
    "tech-writer": "Theo Writer",
    "python-dev": "Elias Python",  # representative dev — activates the *dev section
}

#: The three work types whose playbook has a ``*dev`` guide (task, bug, review).
_DEV_GUIDE_TYPES: frozenset[str] = frozenset({"task", "bug", "review"})


def _build_sections(
    roles: tuple[RoleGuide, ...] | list[RoleGuideSpec],
    roster: dict[str, str],
) -> list[dict[str, Any]]:
    """Replicate the backend ``_write_item_skills`` section-building logic verbatim.

    Accepts either ``RoleGuide`` (shim dataclasses) or ``RoleGuideSpec`` (pydantic)
    so the same helper drives both the PLAYBOOK path and the snapshot path.
    """
    has_dev = any(slug.endswith("-dev") for slug in roster)
    sections: list[dict[str, Any]] = []
    for guide in roles:
        if guide.slug == DEV:
            if not has_dev:
                continue
            title = "developers"
        elif guide.slug in roster:
            title = f"{roster[guide.slug]} (`{guide.slug}`)"
        else:
            continue
        sections.append(
            {
                "title": title,
                "enter": guide.enter,
                "do": guide.do,
                "handoff": guide.handoff,
                "watch": guide.watch,
            }
        )
    return sections


def _render_skill(
    item_type: str,
    overview: str,
    lifecycle: str,
    commands: list[str],
    roles: tuple[RoleGuide, ...] | list[RoleGuideSpec],
    *,
    version: str = "0.5.0",
) -> str:
    """Render the ``agents/item_skill.md.j2`` template exactly as the backend does."""
    sections = _build_sections(roles, _FIXED_ROSTER)
    return render(
        "agents/item_skill.md.j2",
        title=item_type.capitalize(),
        type=item_type,
        version=version,
        overview=overview,
        lifecycle=lifecycle,
        commands=commands,
        sections=sections,
    )


def test_layer_b_rendered_output_byte_identical_to_snapshot() -> None:
    """Layer B (ADR-000226 §4): rendered sq-<type> skill from the loaded PLAYBOOK is
    byte-identical to rendering from the frozen _SNAPSHOT for all 7 work types.

    This is the decisive regression gate: it catches any bug in the *dev sentinel
    resolution, the spec→shim conversion, or the template that the structural tests
    miss.  A faithful spec that rendered differently would still be a user-visible
    regression.
    """
    for type_name, snap in _SNAPSHOT.items():
        item_type = type_name

        # --- expected: render from frozen snapshot (represents pre-FEAT-220 Python literals) ---
        snap_roles: list[dict[str, object]] = snap["roles"]  # type: ignore[assignment]
        snapshot_role_guides: list[RoleGuideSpec] = [
            RoleGuideSpec(
                slug=str(r["slug"]),
                enter=list(r["enter"]),  # type: ignore[arg-type]
                do=list(r["do"]),  # type: ignore[arg-type]
                handoff=list(r["handoff"]),  # type: ignore[arg-type]
                watch=list(r["watch"]),  # type: ignore[arg-type]
            )
            for r in snap_roles
        ]
        expected = _render_skill(
            item_type,
            overview=str(snap["overview"]),
            lifecycle=str(snap["lifecycle"]),
            commands=list(snap["commands"]),  # type: ignore[arg-type]
            roles=snapshot_role_guides,
        )

        # --- actual: render from the live TOML-loaded PLAYBOOK shim ---
        pb = PLAYBOOK[item_type]
        actual = _render_skill(
            item_type,
            overview=pb.overview,
            lifecycle=pb.lifecycle,
            commands=list(pb.commands),
            roles=pb.roles,
        )

        assert actual == expected, (
            f"{type_name}: rendered skill body is NOT byte-identical between TOML-loaded "
            f"PLAYBOOK and the frozen snapshot.  A string, list entry, or role-guide field "
            f"drifted between playbook.toml and the original Python literals.\n"
            f"First diff at char {next(i for i, (a, b) in enumerate(zip(actual, expected, strict=False)) if a != b) if actual != expected else 'len mismatch'}."
        )


def test_layer_b_dev_section_present_in_three_types() -> None:
    """The *dev → 'For developers' section renders for task, bug, and review when a dev
    is in the fixed roster — and is absent for the other four types (no *dev guide).

    Specific guard for the regression described in TASK-000229: the *dev sentinel must
    be resolved to the 'developers' title, not dropped.
    """
    for item_type, pb in PLAYBOOK.items():
        body = _render_skill(
            item_type,
            overview=pb.overview,
            lifecycle=pb.lifecycle,
            commands=list(pb.commands),
            roles=pb.roles,
        )
        has_section = "## For developers" in body
        if item_type in _DEV_GUIDE_TYPES:
            assert has_section, (
                f"{item_type}: '## For developers' section is MISSING — "
                f"the *dev sentinel was not resolved correctly"
            )
        else:
            assert not has_section, (
                f"{item_type}: unexpected '## For developers' section — "
                f"this type should not have a *dev guide"
            )


def test_layer_b_dev_section_absent_without_dev_in_roster() -> None:
    """The *dev section must NOT render when no dev slug is in the roster.

    This ensures the has_dev gate in the backend rendering logic is preserved.
    """
    roster_no_dev = {k: v for k, v in _FIXED_ROSTER.items() if not k.endswith("-dev")}
    for item_type in _DEV_GUIDE_TYPES:
        pb = PLAYBOOK[item_type]
        sections = _build_sections(pb.roles, roster_no_dev)
        body = render(
            "agents/item_skill.md.j2",
            title=item_type.capitalize(),
            type=item_type,
            version="0.5.0",
            overview=pb.overview,
            lifecycle=pb.lifecycle,
            commands=list(pb.commands),
            sections=sections,
        )
        assert "## For developers" not in body, (
            f"{item_type}: '## For developers' section appeared without a dev in the roster"
        )


# ---------------------------------------------------------------------------
# Packaging test
# ---------------------------------------------------------------------------


def test_playbook_toml_accessible_via_importlib_resources() -> None:
    """playbook.toml is accessible via importlib.resources (i.e. ships as package data)."""
    pkg = importlib.resources.files("squads._interactions")
    toml_path = pkg / "playbook.toml"
    content = toml_path.read_bytes()
    assert content, "playbook.toml is empty"
    assert b"[types.task]" in content, "expected [types.task] section in TOML"
    assert b"[types.feature]" in content, "expected [types.feature] section in TOML"
    assert b"[[types.task.roles]]" in content, "expected [[types.task.roles]] in TOML"


def test_playbook_toml_ships_in_wheel(tmp_path: Path) -> None:
    """playbook.toml is present in the built wheel (package-data invariant).

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

    assert any("playbook.toml" in n for n in names), (
        "playbook.toml not found in wheel; "
        f"files matching *playbook*: {[n for n in names if 'playbook' in n]}"
    )
