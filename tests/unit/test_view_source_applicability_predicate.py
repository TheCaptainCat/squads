"""``squads._views.resolve_view_target`` — the predicate a ``sq:view:<name>`` tag's
declared target resolvability is judged by: is it resolvable when read against a host of a
given *type*? Three questions, one call: declared in the spec, presentation template resolves,
and the declared source applies to the host's type.

This module covers the predicate itself and the classification test that binds it — never a
resolved ``Item``, table-driven per source kind over a hosting and a non-hosting host type, plus
two structural properties that make the classification binding rather than advisory:

- **No raise remains in any per-kind resolver** for a condition its own predicate could have
  decided (:func:`test_no_per_kind_resolver_function_raises`) — the raise, when the state is
  reached anyway (the direct-question caller, ``sq workflow view``), lives one level up, in
  :func:`~squads._views.resolve_source`. ``role``'s resolver degrades an unresolvable identity
  (a role item whose slug resolves against neither the catalog nor a project override — not
  decidable from the type alone, so not this kind's precondition either) rather than raising —
  see :func:`test_an_unresolvable_role_identity_degrades_rather_than_raising`.
- **A predicate reads only a type string and the spec/playbook** — never an ``Item``
  (:func:`test_every_applicability_predicate_is_type_scoped_not_item_scoped`), checked off each
  function's own signature rather than trusted by inspection.
"""

import ast
import inspect
import textwrap
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from squads import _views as views
from squads._errors import SquadsError
from squads._interactions import get_playbook_spec
from squads._models._item import Item
from squads._workflow import bundled_spec
from squads._workflow._models import ROSTER_ROLE, ViewSource

SPEC = bundled_spec()
PLAYBOOK = get_playbook_spec()
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


# --------------------------------------------------------------------------- resolve_view_target


def test_an_undeclared_name_is_refused_regardless_of_host_type() -> None:
    reason = views.resolve_view_target("no-such-view", "task", SPEC, PLAYBOOK)
    assert reason is not None
    assert "no declared view" in reason


def test_a_declared_ref_source_view_applies_to_every_host_type() -> None:
    """The one bundled view (``milestone_rollup``, a ``ref`` source) imposes no host
    constraint — resolvable against any declared type, including one that hosts no
    sub-entities at all."""
    for item_type in ("milestone", "task", "epic", "review"):
        assert views.resolve_view_target("milestone_rollup", item_type, SPEC, PLAYBOOK) is None


def _view_over(kind: str) -> ViewSource:
    return ViewSource(kind="subentity", name=kind)


def test_a_subentity_source_applies_only_to_its_hosting_type() -> None:
    """Table-driven against the pure per-kind applicability function directly — no
    spec/template plumbing needed, since applicability never touches either. The fully wired
    end-to-end shape (a real declared view + template, placed and read) is covered in
    ``tests/service/test_view_tag_placement.py`` and
    ``tests/service/test_view_tag_expansion_at_read_time.py``."""
    from squads._workflow._models import ViewSpec

    view = ViewSpec(source=_view_over("finding"))
    assert views._subentity_source_applies(view, "probe", "review", SPEC, PLAYBOOK) is None

    reason = views._subentity_source_applies(view, "probe", "task", SPEC, PLAYBOOK)
    assert reason is not None
    assert "probe" in reason
    assert "finding" in reason
    assert "task" in reason
    assert "hosts" in reason
    assert "subtask" in reason  # names what task hosts instead, not just what it doesn't


def test_a_subentity_source_over_a_type_hosting_no_kind_at_all_names_none() -> None:
    from squads._workflow._models import ViewSpec

    view = ViewSpec(source=_view_over("finding"))
    reason = views._subentity_source_applies(view, "probe", "milestone", SPEC, PLAYBOOK)
    assert reason is not None
    assert "hosts none" in reason


def test_ref_and_subtree_and_self_sources_declare_their_predicate_constantly_true() -> None:
    """Not by omission from the registry -- all three entries exist and unconditionally
    return ``None``, even for an item type that is not declared in the spec at all (the
    predicate never resolves the type before answering "no constraint")."""
    from squads._workflow._models import ViewSpec

    ref_view = ViewSpec(source=ViewSource(kind="ref", name="related"))
    subtree_view = ViewSpec(source=ViewSource(kind="subtree", name="task"))
    self_view = ViewSpec(source=ViewSource(kind="self"))
    for bogus_type in ("no-such-type", ""):
        assert views._ref_source_applies(ref_view, "probe", bogus_type, SPEC, PLAYBOOK) is None
        assert (
            views._subtree_source_applies(subtree_view, "probe", bogus_type, SPEC, PLAYBOOK) is None
        )
        assert views._self_source_applies(self_view, "probe", bogus_type, SPEC, PLAYBOOK) is None


# ---------------------------------------------------------------------------------- role source


def test_a_role_source_applies_only_to_the_role_type() -> None:
    from squads._workflow._models import ViewSpec

    view = ViewSpec(source=ViewSource(kind="role"))
    assert views._role_source_applies(view, "probe", ROSTER_ROLE, SPEC, PLAYBOOK) is None

    reason = views._role_source_applies(view, "probe", "task", SPEC, PLAYBOOK)
    assert reason is not None
    assert "probe" in reason
    assert "task" in reason
    assert ROSTER_ROLE in reason


def test_an_unresolvable_role_identity_degrades_rather_than_raising() -> None:
    """A ``role``-typed host whose slug resolves against neither the catalog nor a project
    override is not decidable from the type alone (it depends on this item's own slug and the
    override tree on disk) — so it is not this kind's precondition either. Unlike a genuine
    per-kind defect, this is the same corpus/spec mismatch every other role reader already
    tolerates: the resolver delegates to ``resolve_role_for_item``
    (:mod:`squads._roles._resolver`), which degrades to ``RoleDef.from_extra_or_item`` instead
    of raising — see the driven end-to-end repro in
    ``tests/service/test_role_playbook_self_views_end_to_end.py`` for the same case through the
    real service seams."""
    item = Item(
        sequence_id=1,
        type=ROSTER_ROLE,
        title="Nobody",
        slug="no-such-role-anywhere",
        status="Active",
        path="agents/roles/no-such-role-anywhere.md",
        created_at=_NOW,
        updated_at=_NOW,
        prefix="ROLE",
    )
    resolved = views._resolve_role_source(item, None)
    assert resolved.slug == "no-such-role-anywhere"
    assert resolved.full_name == "Nobody"


# ------------------------------------------------------------------------- emptiness ≠ failure


def _item(seq: int, item_type: str, prefix: str) -> Item:
    folder = SPEC.items[item_type].folder
    return Item(
        sequence_id=seq,
        type=item_type,
        title="x",
        slug="x",
        status="Draft",
        path=f"{folder}/x{seq}.md",
        created_at=_NOW,
        updated_at=_NOW,
        prefix=prefix,
        subentities=[],
    )


def test_a_hosting_type_with_zero_members_is_not_a_precondition_failure() -> None:
    """The predicate answers "can this resolve", not "will this find anything" -- a review
    with no findings still applies, it just projects zero records (proven at the resolver
    level in test_view_projection_engine.py; proven here at the predicate level, which is what
    the quiet consumers gate on)."""
    assert views.resolve_view_target("milestone_rollup", "milestone", SPEC, PLAYBOOK) is None


# --------------------------------------------------------------------------- structural properties


def _contains_raise(fn: Callable[..., object]) -> bool:
    """Whether *fn*'s own body contains a ``raise`` statement — parsed via :mod:`ast` rather
    than a substring search on its source, which would false-positive on the word "raise"
    appearing in a docstring (as several of this module's do, describing exactly why they
    don't)."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return any(isinstance(node, ast.Raise) for node in ast.walk(tree))


def test_no_per_kind_resolver_function_raises() -> None:
    """The binding classification clause: a resolver may not raise for a condition its kind's
    predicate could have decided. Checked against the actual parsed body of each
    per-kind resolver rather than by inspection or a comment, so a reintroduced raise fails
    this test on sight.

    ``role``'s own body has no ``raise`` either — it is a one-line delegation to
    ``resolve_role_for_item`` (:mod:`squads._roles._resolver`), which contains the ``try``/
    ``except`` that turns an unresolvable identity into a degraded value rather than an
    exception (see :func:`test_an_unresolvable_role_identity_degrades_rather_than_raising`)."""
    per_kind_resolvers = (
        views._resolve_ref_source,
        views._resolve_subtree_source,
        views._resolve_subentity_source,
        views._resolve_role_source,
        views._resolve_playbook_source,
        views._resolve_self_source,
    )
    for fn in per_kind_resolvers:
        assert not _contains_raise(fn), f"{fn.__name__} must not raise; move the check upstream"

    # Control: the dispatcher, which these six do not raise from, must itself still
    # contain one, proving `_contains_raise` actually detects a raise rather than passing
    # vacuously.
    assert _contains_raise(views.resolve_source)


def test_the_dispatcher_is_where_the_direct_question_caller_raises_instead() -> None:
    """The raise removed from the per-kind resolvers above still exists for the one caller
    that needs it unconditionally (`sq workflow view`, via ``resolve_source`` /
    ``ViewsMixin.resolve_view``/``render_view``) -- proven directly against the dispatcher
    rather than only against a service-level CLI path."""
    from squads._models._index import SquadsDB
    from squads._workflow._models import ViewSpec

    task = _item(1, "task", "TASK")
    db = SquadsDB(items={task.sequence_id: task})
    view = ViewSpec(source=_view_over("finding"))
    with pytest.raises(SquadsError, match="hosts"):
        views.resolve_source(view, "probe", task, db, SPEC, PLAYBOOK, lambda: [], None)


def test_every_applicability_predicate_is_type_scoped_not_item_scoped() -> None:
    """A predicate 'may not read the host item's content' -- checked structurally off each
    registered function's own signature: the parameter that carries the host is annotated
    ``str`` (a type name), and no parameter anywhere is annotated :class:`~squads._models
    ._item.Item`. A future kind whose predicate accidentally takes an ``Item`` fails this on
    sight, before anyone has to notice it reads ``.status`` or ``.refs`` by inspection."""
    for kind, fn in views._SOURCE_APPLICABILITY.items():
        params = inspect.signature(fn).parameters
        annotations = [p.annotation for p in params.values()]
        assert Item not in annotations, f"{kind}'s predicate ({fn.__name__}) must not take an Item"
        item_type_param = params["item_type"]
        assert item_type_param.annotation is str, kind


def test_every_declared_source_kind_has_a_registered_applicability_predicate() -> None:
    """Future-proofing the registry itself: every literal ``ViewSource.kind`` value has an
    entry in :data:`~squads._views._SOURCE_APPLICABILITY` -- a new kind with no entry would
    ``KeyError`` at :func:`~squads._views.resolve_view_target` instead of failing here, on a
    test named for exactly this property."""
    from typing import get_args

    declared_kinds = get_args(ViewSource.model_fields["kind"].annotation)
    assert set(declared_kinds) == set(views._SOURCE_APPLICABILITY)
