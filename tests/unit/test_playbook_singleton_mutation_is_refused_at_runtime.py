"""The bundled playbook's immutability was previously by convention only — a plain ``dict``
(``PLAYBOOK``) and a pydantic ``frozen=True`` model whose ``types`` field was still a plain
mutable ``dict`` (``frozen`` blocks attribute *reassignment*, not container mutation). Nothing
in ``src/`` ever did mutate it, but nothing stopped a future caller from succeeding silently and
corrupting the process-wide singleton.

The two carriers get two different strengths of guarantee, both real (not conventional) now:

- ``PLAYBOOK`` (a plain module global, never validated through pydantic) is wrapped in a real
  ``MappingProxyType`` — a mutation attempt raises ``TypeError`` at the call site, at runtime.
- ``PlaybookSpec.types`` is pydantic-validated, and pydantic keeps a ``Mapping``-annotated
  field's actual runtime value as whatever concrete mapping was supplied (a plain ``dict``
  here) rather than coercing it into a read-only wrapper — so this one is a **static** (pyright)
  guarantee only: ``spec.types["x"] = ...`` is a type error under ``pyright --strict``, not a
  runtime one. Both are strictly better than the prior all-convention state.
"""

from types import MappingProxyType

import pytest

from squads._interactions import PLAYBOOK
from squads._interactions._models import PlaybookSpec


def test_playbook_module_constant_is_a_mapping_proxy_not_a_plain_dict() -> None:
    assert isinstance(PLAYBOOK, MappingProxyType)


def test_mutating_the_playbook_module_constant_raises_at_runtime() -> None:
    with pytest.raises(TypeError):
        PLAYBOOK["task"] = PLAYBOOK["task"]  # type: ignore[index]


def test_the_playbook_specs_types_field_is_declared_as_a_mapping_not_a_plain_dict() -> None:
    """Pydantic keeps the runtime value a plain (mutable) dict regardless of this annotation —
    the guarantee this buys is static: pyright rejects ``spec.types["x"] = ...`` because
    ``Mapping`` has no ``__setitem__``. Pinning the annotation is what keeps that guarantee from
    quietly regressing back to ``dict[str, ItemPlaybookSpec]``."""
    from collections.abc import Mapping

    annotation = PlaybookSpec.model_fields["types"].annotation
    assert annotation is not None
    assert getattr(annotation, "__origin__", None) is Mapping
