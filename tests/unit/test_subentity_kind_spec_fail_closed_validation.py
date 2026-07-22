"""``WorkflowSpec``'s ``subentity_kinds`` fail-closed guards (its ``@model_validator``, via
``_check_subentity_kinds``/``_check_completion_status``): an undeclared ``lifecycle`` is caught
(and the completion check skips it rather than double-reporting), a ``completion`` status equal
to the lifecycle's own ``initial`` state is rejected (nothing would ever be "done" at creation),
and two kinds may not share a ``plural`` or a ``local_prefix``.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import SubentityKindSpec, WorkflowSpec


def _spec_dict(
    base: WorkflowSpec, subentity_kinds: dict[str, SubentityKindSpec]
) -> dict[str, object]:
    return {
        "items": dict(base.items),
        "statuses": dict(base.statuses),
        "lifecycles": dict(base.lifecycles),
        "prefix_to_type": dict(base.prefix_to_type),
        "alias_to_type": dict(base.alias_to_type),
        "collections": dict(base.collections),
        "subentity_kinds": subentity_kinds,
        "roles": dict(base.roles),
    }


def test_subentity_kind_undeclared_lifecycle_fails_closed() -> None:
    base = bundled_spec()
    kinds = {
        **base.subentity_kinds,
        "ticket": SubentityKindSpec(
            lifecycle="no_such_lifecycle", completion="Done", plural="tickets", local_prefix="TK"
        ),
    }
    with pytest.raises(SquadsError, match="not declared in lifecycles"):
        WorkflowSpec.model_validate(_spec_dict(base, kinds))


def test_subentity_completion_equal_to_the_initial_status_fails_closed() -> None:
    base = bundled_spec()
    kinds = {
        **base.subentity_kinds,
        "ticket": SubentityKindSpec(
            lifecycle="subentity", completion="Todo", plural="tickets", local_prefix="TK"
        ),
    }
    with pytest.raises(SquadsError, match="nothing is done at creation"):
        WorkflowSpec.model_validate(_spec_dict(base, kinds))


def test_subentity_kind_duplicate_plural_fails_closed() -> None:
    base = bundled_spec()
    kinds = {
        **base.subentity_kinds,
        "ticket": SubentityKindSpec(
            lifecycle="subentity", completion="Done", plural="subtasks", local_prefix="TK"
        ),
    }
    with pytest.raises(SquadsError, match="duplicate subentity plural"):
        WorkflowSpec.model_validate(_spec_dict(base, kinds))


def test_subentity_kind_duplicate_local_prefix_fails_closed() -> None:
    base = bundled_spec()
    kinds = {
        **base.subentity_kinds,
        "ticket": SubentityKindSpec(
            lifecycle="subentity", completion="Done", plural="tickets", local_prefix="ST"
        ),
    }
    with pytest.raises(SquadsError, match="duplicate subentity local_prefix"):
        WorkflowSpec.model_validate(_spec_dict(base, kinds))
