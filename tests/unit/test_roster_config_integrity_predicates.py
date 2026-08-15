"""Roster config-integrity clause predicates (``no_live_role``, ``preloaded_skill``), evaluated
directly against a hand-built index snapshot. These are the pure functions both the `sq check`
reporter and the retirement gate call — pinning their behaviour here, independent of either
caller, is what lets the gate reuse them unchanged.
"""

from datetime import UTC, datetime

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, make_ref
from squads._services._config_integrity import (
    ALWAYS_ON_FLOOR,
    NO_LIVE_ROLE,
    PRELOADED_SKILL,
    SCOPED_EDGE,
    TYPE_IMPLIED,
    _always_on_floor,
    check_all,
    check_no_live_role,
    check_preloaded_skill,
    render_finding,
)
from squads._workflow import bundled_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_SPEC = bundled_spec()


def _role(
    seq: int, *, status: str = "Active", is_default: bool = False, slug: str | None = None
) -> Item:
    slug = slug or f"role-{seq}"
    extra: dict[str, object] = {X.SLUG: slug}
    if is_default:
        extra[X.IS_DEFAULT] = True
    return Item(
        sequence_id=seq,
        type="role",
        prefix=BUILTIN_PREFIX["role"],
        title=slug,
        slug=slug,
        status=status,
        path=f"{BUILTIN_FOLDER['role']}/{BUILTIN_PREFIX['role']}-{seq:06d}-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        extra=extra,
    )


def _skill(
    seq: int, *, status: str = "Active", slug: str | None = None, refs: tuple[str, ...] = ()
) -> Item:
    slug = slug or f"skill-{seq}"
    return Item(
        sequence_id=seq,
        type="skill",
        prefix=BUILTIN_PREFIX["skill"],
        title=slug,
        slug=slug,
        status=status,
        path=f"{BUILTIN_FOLDER['skill']}/{BUILTIN_PREFIX['skill']}-{seq:06d}-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        refs=list(refs),
        extra={X.SLUG: slug},
    )


def _db(*items: Item) -> SquadsDB:
    db = SquadsDB(counter=len(items))
    for it in items:
        db.add(it)
    return db


# --------------------------------------------------------------------------- no_live_role


def test_no_live_role_fires_when_no_role_is_live_while_a_backend_is_active() -> None:
    db = _db(_role(1, status="Archived"))
    findings = check_no_live_role(db, _SPEC, ["claude_code"])
    assert [f.clause for f in findings] == [NO_LIVE_ROLE]
    assert findings[0].entry == ""
    assert findings[0].kind is None
    assert findings[0].remedy == "activate another role first"
    assert "remedy" not in findings[0].message  # the remedy lives in its own field, not baked in


def test_no_live_role_stays_silent_with_no_active_backends() -> None:
    db = _db(_role(1, status="Archived"))
    assert check_no_live_role(db, _SPEC, []) == []


def test_no_live_role_stays_silent_when_at_least_one_role_is_live() -> None:
    db = _db(_role(1, status="Active"), _role(2, status="Archived"))
    assert check_no_live_role(db, _SPEC, ["claude_code"]) == []


def test_no_live_role_fires_on_an_empty_roster_with_an_active_backend() -> None:
    db = _db()
    findings = check_no_live_role(db, _SPEC, ["claude_code"])
    assert len(findings) == 1


# --------------------------------------------------------------------------- always_on_floor


def test_always_on_floor_derivation_is_the_intersection_of_every_live_roles_preload_list() -> None:
    """The floor is derived from ``skills_for_role``, not restated as a fixed name list —
    proven by moving the resolver's implied set and watching the derivation move with it."""
    manager = _role(1, status="Active", slug="manager")  # bundled: no PLAYBOOK entry of its own
    devops = _role(2, status="Active", slug="devops")  # bundled: also no PLAYBOOK entry

    floor = _always_on_floor([manager, devops], _SPEC)

    assert floor == {"squads", "greeting", "sq-memory"}


def test_always_on_floor_shrinks_when_the_live_roles_no_longer_share_a_skill(
    monkeypatch,
) -> None:
    """Moving the resolver's implied set moves the derivation: a role whose resolved preload
    list gains an extra shared skill widens the floor, and a role that does not share it
    narrows it straight back down — proving this is read live off the resolver, never a
    restated list of names."""
    import squads._services._config_integrity as config_integrity

    def _fake_skills_for_role(slug: str, spec: object = None, playbook: object = None) -> list[str]:
        base = ["squads", "greeting", "sq-memory"]
        if slug == "manager":
            return [*base, "extra-shared-skill"]
        return base

    monkeypatch.setattr(config_integrity, "skills_for_role", _fake_skills_for_role)
    manager = _role(1, status="Active", slug="manager")

    assert _always_on_floor([manager], _SPEC) == {
        "squads",
        "greeting",
        "sq-memory",
        "extra-shared-skill",
    }

    devops = _role(2, status="Active", slug="devops")  # does not share "extra-shared-skill"
    assert _always_on_floor([manager, devops], _SPEC) == {"squads", "greeting", "sq-memory"}


def test_always_on_floor_of_an_empty_role_set_is_empty_not_everything() -> None:
    """The vacuous-intersection guard: mathematically an intersection over zero sets is the
    universe, which would wrongly floor every non-live skill. Guarded to empty instead."""
    assert _always_on_floor([], _SPEC) == frozenset()


# --------------------------------------------------------------------------- preloaded_skill


def test_preloaded_skill_fires_for_an_archived_always_on_skill_while_a_role_is_live() -> None:
    """The foundation-skill shape: an always-on-floor skill archived with nothing ever
    refusing it."""
    role = _role(1, status="Active")
    skill = _skill(2, status="Archived", slug="squads")
    findings = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])
    assert [f.clause for f in findings] == [PRELOADED_SKILL]
    assert findings[0].entry == skill.id
    assert findings[0].kind == ALWAYS_ON_FLOOR
    assert findings[0].severable_targets == frozenset()
    assert findings[0].remedy is None  # no code path from which one could ever be offered
    assert "permanent floor" in findings[0].message
    assert "no remedy" in findings[0].message  # the message states the fact; nothing to append


def test_preloaded_skill_always_on_floor_fires_with_no_active_backend() -> None:
    """The one kind exempt from the family's backend condition: its authority is a declared
    rule of the roster contract, not a derived property of the projection."""
    role = _role(1, status="Active")
    skill = _skill(2, status="Archived", slug="squads")
    findings = check_preloaded_skill(_db(role, skill), _SPEC, [])
    assert [f.kind for f in findings] == [ALWAYS_ON_FLOOR]


def test_preloaded_skill_fires_for_an_archived_type_implied_skill_and_names_the_type() -> None:
    role = _role(1, status="Active", slug="tech-lead")  # tech-lead's playbook interacts with task
    skill = _skill(2, status="Archived", slug="sq-task")
    findings = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])
    assert findings[0].entry == skill.id
    assert findings[0].kind == TYPE_IMPLIED
    assert findings[0].severable_targets == frozenset()
    assert "implied by declared type" in findings[0].message
    assert "task" in findings[0].message
    assert "remedy" not in findings[0].message  # remedy lives in its own field, not baked in
    assert findings[0].remedy is not None
    assert "make the skill live again" in findings[0].remedy
    assert "drop the implicating type" in findings[0].remedy


def test_preloaded_skill_type_implied_stays_silent_with_no_active_backend() -> None:
    role = _role(1, status="Active", slug="tech-lead")
    skill = _skill(2, status="Archived", slug="sq-task")
    assert check_preloaded_skill(_db(role, skill), _SPEC, []) == []


def test_preloaded_skill_fires_for_an_archived_custom_skill_still_scoped_to_a_live_role() -> None:
    role = _role(1, status="Active", slug="python-dev")
    skill = _skill(
        2, status="Archived", slug="my-custom-skill", refs=(make_ref(role.id, "scopes"),)
    )
    findings = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])
    assert findings[0].entry == skill.id
    assert findings[0].kind == SCOPED_EDGE
    assert findings[0].severable_targets == frozenset({role.id})
    assert "scoped to live role" in findings[0].message
    assert "python-dev" in findings[0].message
    assert "remedy" not in findings[0].message
    assert findings[0].remedy == "pass --unlink, or run `sq skill <addr> unlink-role <role>` first"


def test_preloaded_skill_scoped_edge_stays_silent_with_no_active_backend() -> None:
    role = _role(1, status="Active", slug="python-dev")
    skill = _skill(
        2, status="Archived", slug="my-custom-skill", refs=(make_ref(role.id, "scopes"),)
    )
    assert check_preloaded_skill(_db(role, skill), _SPEC, []) == []


def test_preloaded_skill_stays_silent_when_the_scoping_role_is_itself_not_live() -> None:
    live = _role(1, status="Active", slug="manager")
    archived_scope = _role(2, status="Archived", slug="python-dev")
    skill = _skill(
        3, status="Archived", slug="my-custom-skill", refs=(make_ref(archived_scope.id, "scopes"),)
    )
    assert check_preloaded_skill(_db(live, archived_scope, skill), _SPEC, ["claude_code"]) == []


def test_preloaded_skill_stays_silent_when_no_role_is_live_at_all() -> None:
    role = _role(1, status="Archived", slug="tech-lead")
    skill = _skill(2, status="Archived", slug="sq-task")
    assert check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"]) == []


def test_preloaded_skill_stays_silent_for_a_live_skill() -> None:
    role = _role(1, status="Active")
    skill = _skill(2, status="Active", slug="squads")
    assert check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"]) == []


def test_preloaded_skill_caps_and_summarises_a_widely_scoped_skill() -> None:
    roles = [_role(i, status="Active", slug=f"role-{i}") for i in range(1, 8)]  # 7 roles
    refs = tuple(make_ref(r.id, "scopes") for r in roles)
    skill = _skill(100, status="Archived", slug="my-custom-skill", refs=refs)
    findings = check_preloaded_skill(_db(*roles, skill), _SPEC, ["claude_code"])
    assert len(findings) == 1
    assert "and 2 more" in findings[0].message  # 7 scoped roles, cap 5 -> 2 in the tail


def test_preloaded_skill_reports_both_kinds_for_a_doubly_dependent_skill() -> None:
    """A skill simultaneously scoped to a live role AND implied by a declared type produces one
    finding per kind, not just the type-implied one — reporting only the highest-remedy kind a
    skill happens to be caught by would hide the other, equally real dependency."""
    role = _role(1, status="Active", slug="tech-lead")  # implies sq-task
    skill = _skill(2, status="Archived", slug="sq-task", refs=(make_ref(role.id, "scopes"),))
    findings = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])
    assert [f.kind for f in findings] == [SCOPED_EDGE, TYPE_IMPLIED]  # declared severable-to-none
    assert all(f.entry == skill.id for f in findings)
    scoped_edge_finding = findings[0]
    assert scoped_edge_finding.severable_targets == frozenset({role.id})
    assert "tech-lead" in scoped_edge_finding.message
    type_implied_finding = findings[1]
    assert "task" in type_implied_finding.message


# --------------------------------------------------------------------------- composition


def test_check_all_concatenates_every_clause_in_order() -> None:
    live = _role(1, status="Active", slug="tech-lead")
    skill = _skill(2, status="Archived", slug="squads")
    findings = check_all(_db(live, skill), _SPEC, ["claude_code"])
    assert [f.clause for f in findings] == [PRELOADED_SKILL]  # no_live_role silent; one live role


def test_check_all_orders_no_live_role_ahead_of_preloaded_skill() -> None:
    """Deterministic cross-clause ordering: both clauses can never co-fire on the same squad
    (``no_live_role`` needs zero live roles; ``preloaded_skill`` needs at least one), so this
    exercises each clause firing alone, checking ``check_all``'s own fixed order."""
    empty = _db()
    assert [f.clause for f in check_all(empty, _SPEC, ["claude_code"])] == [NO_LIVE_ROLE]


# ----------------------------------------------------------------------- render_finding


def _assert_no_phrase_repeats(rendered: str) -> None:
    """A cheap, general regression guard for the composition bug this module fixed: no
    multi-word phrase from the rendered line should appear twice. Splits on the em-dash
    section separator ``render_finding`` itself uses, so a condition and a remedy that happen
    to share a short word (e.g. "role") never false-positive — only a whole repeated segment
    does."""
    segments = [s.strip() for s in rendered.split(" — ") if s.strip()]
    assert len(segments) == len(set(segments)), (
        f"a rendered segment repeats verbatim, the exact composition bug this guards against: "
        f"{rendered!r}"
    )


def test_render_finding_no_live_role_composes_condition_and_remedy_exactly_once() -> None:
    db = _db(_role(1, status="Archived"))
    finding = check_no_live_role(db, _SPEC, ["claude_code"])[0]
    rendered = render_finding(finding)
    assert rendered == (
        "no role entry is live, but backend(s) claude_code are active — the generated config "
        "can present no agent — remedy: activate another role first"
    )
    assert rendered.count("remedy") == 1
    _assert_no_phrase_repeats(rendered)


def test_render_finding_scoped_edge_defaults_to_the_no_unlink_remedy() -> None:
    """The default (``unlink_available=False``) is the report-mode situation: no transition is
    in play, so ``--unlink`` — a flag on a status command — is never something to offer."""
    role = _role(1, status="Active", slug="python-dev")
    skill = _skill(
        2, status="Archived", slug="my-custom-skill", refs=(make_ref(role.id, "scopes"),)
    )
    finding = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])[0]
    rendered = render_finding(finding)
    assert rendered == (
        "not live (status 'Archived') but still scoped to live role(s): python-dev — remedy: "
        "sever the edge with `sq skill <addr> unlink-role <role>`, or reactivate the skill"
    )
    assert "--unlink" not in rendered
    assert rendered.count("remedy") == 1
    _assert_no_phrase_repeats(rendered)


def test_render_finding_scoped_edge_offers_unlink_when_available() -> None:
    """A retirement of the finding's own entry: ``--unlink`` is a real option on that command,
    so ``unlink_available=True`` restores it as the first-named step."""
    role = _role(1, status="Active", slug="python-dev")
    skill = _skill(
        2, status="Archived", slug="my-custom-skill", refs=(make_ref(role.id, "scopes"),)
    )
    finding = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])[0]
    rendered = render_finding(finding, unlink_available=True)
    assert rendered == (
        "not live (status 'Archived') but still scoped to live role(s): python-dev — remedy: "
        "pass --unlink, or run `sq skill <addr> unlink-role <role>` first"
    )
    assert rendered.count("remedy") == 1
    _assert_no_phrase_repeats(rendered)


def test_render_finding_type_implied_composes_condition_and_remedy_exactly_once() -> None:
    role = _role(1, status="Active", slug="tech-lead")
    skill = _skill(2, status="Archived", slug="sq-task")
    finding = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])[0]
    rendered = render_finding(finding)
    assert rendered == (
        "not live (status 'Archived') but implied by declared type(s): task — remedy: make "
        "the skill live again, or drop the implicating type via `[selected]` in "
        ".overrides/workflow.toml"
    )
    assert rendered.count("remedy") == 1
    _assert_no_phrase_repeats(rendered)


def test_render_finding_always_on_floor_composes_the_condition_alone_with_no_remedy_line() -> None:
    """The one kind with no remedy: the condition already states "no remedy exists" as a fact
    about the state (not an instruction), and — the bug this guards against — nothing further
    is appended on top of it."""
    role = _role(1, status="Active")
    skill = _skill(2, status="Archived", slug="squads")
    finding = check_preloaded_skill(_db(role, skill), _SPEC, ["claude_code"])[0]
    rendered = render_finding(finding)
    assert rendered == (
        "not live (status 'Archived') but every role preloads it unconditionally — a "
        "permanent floor of the roster contract; no remedy exists"
    )
    assert rendered.count("remedy") == 1  # appears once, as a fact — never a second "remedy:" tail
    assert "remedy:" not in rendered  # no dangling "remedy: <text>" clause was appended
    _assert_no_phrase_repeats(rendered)


# ------------------------------------------------------------------- no clause label anywhere


def test_no_finding_message_or_remedy_ever_names_the_clause_or_kind_identifier() -> None:
    """A clause identifier is internal — code, the ref-kind declaration, tests, the decision
    that governs this module — and never appears in user-facing text. ``render_finding``'s
    output is exactly the user-facing text, so it must never contain the internal
    identifiers."""
    role = _role(1, status="Active", slug="tech-lead")
    skill_floor = _skill(2, status="Archived", slug="squads")
    skill_type = _skill(3, status="Archived", slug="sq-task")
    skill_scoped = _skill(
        4, status="Archived", slug="my-custom-skill", refs=(make_ref(role.id, "scopes"),)
    )
    db = _db(role, skill_floor, skill_type, skill_scoped)
    banned = {
        "no_live_role",
        "preloaded_skill",
        "scoped_edge",
        "type_implied",
        "always_on_floor",
        "C1",
        "C2",
        "C3",
    }
    for finding in check_all(db, _SPEC, ["claude_code"]):
        rendered = render_finding(finding)
        for word in banned:
            assert word not in rendered
