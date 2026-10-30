"""Repo-hygiene gate: the OpenAPI document describes every operation of the table with the
properties of its answer, no `GET` request carries a nested field (a query string is flat), and
every write that compares `If-Match` is an operation of the table."""

from typing import Any

from squads._api._ops import CONDITIONAL_WRITES, OPERATIONS, ROUTED_OPERATIONS
from squads._daemon._openapi import build_document


def _resolve(document: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    return document["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def test_the_document_describes_every_operation_and_lists_its_answer_properties() -> None:
    document = build_document("x")
    problems: list[str] = []
    for op in ROUTED_OPERATIONS:
        method, path = op.route
        described = document["paths"].get(path, {}).get(method.lower())
        if described is None or described["operationId"] != op.name:
            problems.append(f"{op.name}: not described at {method} {path}")
            continue
        answer = described["responses"]["200"]["content"]["application/json"]["schema"]
        data = _resolve(document, _resolve(document, answer)["properties"]["data"])
        if not data.get("properties"):
            problems.append(f"{op.name}: its response schema lists no properties")
    assert not problems, "\n".join(problems)


def test_no_get_request_declares_a_nested_field() -> None:
    nested = [
        f"{op.name}.{name}"
        for op in ROUTED_OPERATIONS
        if op.method == "GET"
        for name, field in op.request.model_fields.items()
        if not _flat(field.annotation)
    ]
    assert not nested, f"a GET request holds a nested field: {nested}"


def _flat(annotation: Any) -> bool:
    from types import UnionType
    from typing import Union, get_args, get_origin

    if get_origin(annotation) in (Union, UnionType):
        return all(_flat(a) for a in get_args(annotation))
    if get_origin(annotation) is list:
        return all(_flat(a) for a in get_args(annotation))
    return annotation in (str, int, float, bool, type(None))


def test_every_conditional_write_is_an_operation_of_the_table() -> None:
    names = {op.name for op in OPERATIONS}
    assert names >= CONDITIONAL_WRITES
    assert all(
        op.method != "GET" and not op.local_only
        for op in OPERATIONS
        if op.name in CONDITIONAL_WRITES
    )


def test_no_literal_segment_sits_beside_a_parameter_unless_its_slugs_are_refused() -> None:
    """A literal beside a parameter is reachable only if the parameter refuses it as a value."""
    from squads._models._participants import ROLE_GROUP_VERBS, SKILL_GROUP_VERBS

    refused: dict[tuple[str, ...], frozenset[str]] = {
        ("v1", "roles"): ROLE_GROUP_VERBS,
        ("v1", "skills"): SKILL_GROUP_VERBS,
    }
    shapes = {tuple(op.route[1].strip("/").split("/")) for op in ROUTED_OPERATIONS}
    problems: list[str] = []
    for shape in sorted(shapes):
        for other in sorted(shapes):
            for i, segment in enumerate(shape):
                if (
                    segment.startswith("{")
                    and len(other) > i
                    and shape[:i] == other[:i]
                    and not other[i].startswith("{")
                    and other[i] not in refused.get(shape[:i], frozenset())
                ):
                    problems.append(f"/{'/'.join(other)} beside /{'/'.join(shape)}")
    assert not problems, "\n".join(problems)
